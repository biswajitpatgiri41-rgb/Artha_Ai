import type { AssistantMessageRecord } from './assistant-types';
import type { PageAssistantContext } from './assistant-context';

export interface AssistantChatResponse {
  answer: string;
  page_context: string;
  model: string;
  warnings: string[];
}

export interface AssistantApiError extends Error {
  status?: number;
  code?: string;
  safeMessage: string;
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

function mapHttpError(status: number): { code: string; safeMessage: string } {
  switch (status) {
    case 404:
      return { code: 'NOT_FOUND', safeMessage: 'Assistant endpoint not found' };
    case 422:
      return { code: 'VALIDATION_ERROR', safeMessage: 'Assistant request could not be processed' };
    case 500:
      return { code: 'SERVER_ERROR', safeMessage: 'AI assistant is temporarily unavailable' };
    case 502:
      return { code: 'PROVIDER_UNAVAILABLE', safeMessage: 'AI provider is currently unavailable' };
    case 503:
      return { code: 'SERVICE_UNAVAILABLE', safeMessage: 'AI provider is not configured' };
    case 504:
      return { code: 'TIMEOUT', safeMessage: 'AI provider timed out. Please try again' };
    case 429:
      return { code: 'RATE_LIMIT', safeMessage: 'AI request limit reached. Please try again shortly' };
    default:
      return { code: 'UNKNOWN', safeMessage: 'AI assistant is temporarily unavailable' };
  }
}

export interface EvidenceItem {
  evidence_id: string;
  filename: string;
  format: string;
  location: {
    page?: number;
    section?: string;
    chunk_id?: string;
    rows?: number[];
    columns?: string[];
    sheet?: string;
    path?: string;
    keys?: string[];
  };
  excerpt?: string;
  structured_result?: unknown;
  retrieval_score?: number;
  retrieved_at: string;
  run_id: string;
}

export async function sendAssistantMessage(input: {
  message: string;
  page: string;
  pageContext: string;
  pageData: PageAssistantContext | null;
  conversation: AssistantMessageRecord[];
  documentEvidence?: EvidenceItem[];
  documentEvidenceRunId?: string;
  documentEvidenceIds?: string[];
}): Promise<AssistantChatResponse> {
  const url = `${apiBaseUrl}/assistant/chat`;
  const isDevelopment = process.env.NODE_ENV === 'development';

  if (isDevelopment) {
    console.log('[Assistant] Request:', { url, page: input.page, messageLength: input.message.length, evidenceCount: input.documentEvidenceIds?.length ?? input.documentEvidence?.length ?? 0 });
  }

  // Timeout to match backend (300s) + buffer
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 320000);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: input.message,
        page: input.page,
        page_context: input.pageContext,
        page_data: input.pageData,
        conversation: input.conversation.slice(-20).map(({ role, content }) => ({ role, content })),
        document_evidence: input.documentEvidence,
        document_evidence_run_id: input.documentEvidenceRunId,
        document_evidence_ids: input.documentEvidenceIds,
      }),
      signal: controller.signal,
    });

    if (isDevelopment) {
      console.log('[Assistant] Response:', { status: response.status, url });
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const { code, safeMessage } = mapHttpError(response.status);
      
      const error = new Error(safeMessage) as AssistantApiError;
      error.status = response.status;
      error.code = code;
      error.safeMessage = safeMessage;
      
      if (isDevelopment) {
        // Use console.warn for expected HTTP failures to avoid Next.js error overlay
        console.warn('[Assistant] Request failed', {
          status: response.status,
          code,
          message: safeMessage,
          detail: errorData.detail
        });
      }
      
      throw error;
    }

    const data = await response.json() as AssistantChatResponse;
    return data;

  } catch (err) {
    if (err instanceof Error && 'status' in err) {
      // Already mapped error - rethrow
      throw err;
    }
    
    // Network error or other failure
    const error = new Error('Assistant backend is not running') as AssistantApiError;
    error.code = 'NETWORK_ERROR';
    error.safeMessage = 'Assistant backend is not running';
    
    if (isDevelopment) {
      // Use console.warn for expected network failures to avoid Next.js error overlay
      console.warn('[Assistant] Network error:', { url, error: err instanceof Error ? err.message : String(err) });
    }
    
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}
