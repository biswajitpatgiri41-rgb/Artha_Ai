export type AssistantMessageRole = 'user' | 'assistant';

export type AssistantState = 'idle' | 'sending' | 'receiving' | 'error';

export interface AssistantMessageRecord {
  id: string;
  role: AssistantMessageRole;
  content: string;
  warnings?: string[];
  badge?: 'Data not connected' | 'Mock context' | 'Conceptual explanation';
  isRegenerating?: boolean;
}

export interface AssistantConversation {
  messages: AssistantMessageRecord[];
  pageContextEnabled: boolean;
}