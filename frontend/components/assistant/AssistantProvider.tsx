'use client';

import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { getPageContext, type PageAssistantContext } from '@/lib/assistant-context';
import type { AssistantMessageRecord, AssistantState, AssistantConversation } from '@/lib/assistant-types';
import { sendAssistantMessage, type AssistantApiError } from '@/lib/assistant-api';
import { AssistantButton } from './AssistantButton';
import { AssistantPageContextProvider } from './AssistantContext';
import { AssistantPanel } from './AssistantPanel';

const MAX_HISTORY = 20;
const STORAGE_KEY = 'policy-assistant-conversations';
const EVIDENCE_RUN_ID_KEY = 'india-monetary-policy-evidence-run-id';
const EVIDENCE_SELECTED_KEY = 'india-monetary-policy-evidence-selected';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function determineBadge(warnings: string[] | undefined): 'Data not connected' | 'Mock context' | 'Conceptual explanation' | undefined {
  if (!warnings?.length) return undefined;
  const text = warnings.join(' ').toLowerCase();
  if (text.includes('mock') || text.includes('demo')) return 'Mock context';
  if (text.includes('not connected') || text.includes('cannot be verified') || text.includes('unavailable')) return 'Data not connected';
  return 'Conceptual explanation';
}

export function AssistantProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [pageData, setPageData] = useState<PageAssistantContext | null>(null);
  const [state, setState] = useState<AssistantState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [contextNotice, setContextNotice] = useState<string | null>(null);
  const [evidenceEnabled, setEvidenceEnabled] = useState(false);

  // Per-page conversation history with page context toggle
  const [conversations, setConversations] = useState<Record<string, AssistantConversation>>({});

  const context = getPageContext(pathname);
  const activePageData = pageData?.page === pathname ? pageData : context.defaultPageData;

  // Get current page's conversation
  const currentConversation = conversations[pathname] ?? { messages: [], pageContextEnabled: true };
  const messages = currentConversation.messages;
  // Send only explicitly selected IDs. The backend retrieves query-matched
  // excerpts from this run before constructing the model context.
  const getSelectedEvidenceContext = useCallback(async (): Promise<{ runId: string; evidenceIds: string[] } | undefined> => {
    const runId = pageData?.run_id ?? window.sessionStorage.getItem(EVIDENCE_RUN_ID_KEY);
    if (!runId) throw new Error('No evidence session was found. Open Evidence Workspace and reload the uploaded files.');
    let evidenceIds: string[] = [];
    try { const parsed: unknown = JSON.parse(window.sessionStorage.getItem(EVIDENCE_SELECTED_KEY) ?? '[]'); evidenceIds = Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === 'string').slice(0, 100) : []; } catch { evidenceIds = []; }
    if (evidenceIds.length === 0) return undefined;
    return { runId, evidenceIds };
  }, [pageData?.run_id]);

  // Load conversations from sessionStorage on mount
  useEffect(() => {
    const loadConversations = () => {
      try {
        const saved = window.sessionStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved) as Record<string, AssistantConversation>;
          const normalized: Record<string, AssistantConversation> = {};
          Object.entries(parsed).forEach(([key, value]) => {
            if (Array.isArray(value)) {
              normalized[key] = { messages: value as AssistantMessageRecord[], pageContextEnabled: true };
            } else {
              normalized[key] = value;
            }
          });
          // Defer state update to avoid cascading renders
          setConversations((prev) => ({ ...prev, ...normalized }));
        }
      } catch {}
    };

    // Defer the load to avoid synchronous setState in effect
    const timer = setTimeout(loadConversations, 0);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    try { window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(conversations)); } catch {}
  }, [conversations]);

  useEffect(() => {
    if (isOpen) {
      // Use setTimeout to defer state update, avoiding cascading renders
      const noticeTimer = setTimeout(() => {
        setContextNotice('Context changed to ' + context.title);
        const clearTimer = setTimeout(() => setContextNotice(null), 3000);
        return () => clearTimeout(clearTimer);
      }, 0);
      return () => clearTimeout(noticeTimer);
    }
  }, [pathname, isOpen, context.title]);

  const updateConversation = useCallback((newMessages: AssistantMessageRecord[]) => {
    setConversations((current) => ({
      ...current,
      [pathname]: { messages: newMessages.slice(-MAX_HISTORY), pageContextEnabled: current[pathname]?.pageContextEnabled ?? true }
    }));
  }, [pathname]);

  const clearConversation = useCallback(() => {
    setConversations((current) => ({
      ...current,
      [pathname]: { messages: [], pageContextEnabled: current[pathname]?.pageContextEnabled ?? true }
    }));
  }, [pathname]);

  const togglePageContext = useCallback(() => {
    setConversations((current) => ({
      ...current,
      [pathname]: { ...current[pathname], pageContextEnabled: !current[pathname]?.pageContextEnabled }
    }));
  }, [pathname]);
const sendMessage = useCallback(async (messageText: string, contextOverride?: PageAssistantContext | null) => {
    if (!messageText.trim() || state !== 'idle') return;
    const userMessage: AssistantMessageRecord = { id: generateId(), role: 'user', content: messageText.trim() };
    updateConversation([...messages, userMessage]);
    setState('sending'); setError(null);
    try {
      setState('receiving');
      const pageDataToSend = contextOverride ?? (currentConversation.pageContextEnabled ? activePageData : null);
      const evidenceContext = evidenceEnabled ? await getSelectedEvidenceContext() : undefined;
      const response = await sendAssistantMessage({ message: messageText.trim(), page: pathname, pageContext: context.title, pageData: pageDataToSend, conversation: messages, documentEvidenceRunId: evidenceContext?.runId, documentEvidenceIds: evidenceContext?.evidenceIds });
      const badge = determineBadge(response.warnings);
      const assistantMessage: AssistantMessageRecord = { id: generateId(), role: 'assistant', content: response.answer, warnings: response.warnings, badge };
      updateConversation([...messages, userMessage, assistantMessage]);
    } catch (err) {
      const apiError = err as AssistantApiError;
      const safeMessage = apiError.safeMessage ?? (err instanceof Error ? err.message : 'Assistant request failed');
      setError(safeMessage);
      updateConversation([...messages, userMessage]);
      setState('error');
    } finally {
      setState('idle');
    }
  }, [messages, pathname, context.title, activePageData, currentConversation.pageContextEnabled, evidenceEnabled, getSelectedEvidenceContext, updateConversation]);

  useEffect(() => {
    const handleAskWhy = (event: Event) => {
      const detail = (event as CustomEvent<{ chartId: string; pageData: PageAssistantContext }>).detail;
      if (!detail?.chartId || !detail.pageData) return;
      setPageData(detail.pageData);
      setIsOpen(true); setIsMinimized(false);
      const question = `Ask Why? Explain the displayed chart “${detail.chartId}” using the attached structured chart context and any explicitly enabled uploaded evidence. Distinguish observed movement, predictive attribution, scenario effect, and causal estimate. Do not invent causal explanations or numerical contributions; if attribution is unavailable, explain only verifiable context and state the limitation.`;
      void sendMessage(question, detail.pageData);
    };
    window.addEventListener('assistant:ask-why', handleAskWhy);
    return () => window.removeEventListener('assistant:ask-why', handleAskWhy);
  }, [sendMessage]);

  const regenerateMessage = useCallback(async () => {
    if (messages.length < 2 || state !== 'idle') return;
    const lastUserIndex = messages.findLastIndex((m) => m.role === 'user');
    if (lastUserIndex === -1) return;
    const userMessage = messages[lastUserIndex];
    const messagesBeforeLastUser = messages.slice(0, lastUserIndex);
    updateConversation([...messagesBeforeLastUser, userMessage]);
    setState('sending'); setError(null);
    try {
      setState('receiving');
      const pageDataToSend = currentConversation.pageContextEnabled ? activePageData : null;
      const evidenceContext = evidenceEnabled ? await getSelectedEvidenceContext() : undefined;
      const response = await sendAssistantMessage({ message: userMessage.content, page: pathname, pageContext: context.title, pageData: pageDataToSend, conversation: messagesBeforeLastUser, documentEvidenceRunId: evidenceContext?.runId, documentEvidenceIds: evidenceContext?.evidenceIds });
      const badge = determineBadge(response.warnings);
      const assistantMessage: AssistantMessageRecord = { id: generateId(), role: 'assistant', content: response.answer, warnings: response.warnings, badge };
      updateConversation([...messagesBeforeLastUser, userMessage, assistantMessage]);
    } catch (err) {
      const apiError = err as AssistantApiError;
      const safeMessage = apiError.safeMessage ?? (err instanceof Error ? err.message : 'Assistant request failed');
      setError(safeMessage);
      updateConversation(messages);
      setState('error');
    } finally {
      setState('idle');
    }
  }, [messages, pathname, context.title, activePageData, currentConversation.pageContextEnabled, evidenceEnabled, getSelectedEvidenceContext, updateConversation]);

  const openAssistant = useCallback(() => { setIsOpen(true); setIsMinimized(false); }, []);

  return (
    <AssistantPageContextProvider pageData={pageData} setPageData={setPageData}>
      {children}
      {!isOpen && <AssistantButton onClick={openAssistant} />}
      {isOpen && (
        <AssistantPanel
          context={context}
          pageData={activePageData}
          messages={messages}
          state={state}
          error={error}
          contextNotice={contextNotice}
          pageContextEnabled={currentConversation.pageContextEnabled}
          evidenceEnabled={evidenceEnabled}
          onConversationChange={updateConversation}
          onNewConversation={clearConversation}
          onSendMessage={sendMessage}
          onRegenerate={regenerateMessage}
          onTogglePageContext={togglePageContext}
          onToggleEvidence={() => setEvidenceEnabled((v) => !v)}
          isMinimized={isMinimized}
          onClose={() => setIsOpen(false)}
          onMinimize={() => setIsMinimized((value) => !value)}
        />
      )}
    </AssistantPageContextProvider>
  );
}
