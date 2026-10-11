import { Copy, RotateCcw, Loader2 } from 'lucide-react';
import type { AssistantMessageRecord } from '@/lib/assistant-types';
import type { AssistantState } from '@/lib/assistant-types';

interface AssistantMessageProps {
  message: AssistantMessageRecord;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
  state?: AssistantState;
}

export function AssistantMessage({ message, onRegenerate, isRegenerating, state }: AssistantMessageProps) {
  const isUser = message.role === 'user';
  const isLastAssistant = !isUser && onRegenerate;
  const isBusy = state === 'sending' || state === 'receiving' || isRegenerating;

  return (
    <article data-testid={isUser ? 'assistant-message-user' : 'assistant-message-assistant'} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[88%] rounded-2xl border px-3 py-2.5 text-xs leading-5 ${isUser ? 'border-blue-300/20 bg-blue-500/15 text-blue-50' : 'border-white/[0.08] bg-white/[0.04] text-slate-300'}`}>
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!isUser && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {message.badge && (
              <span data-testid="assistant-badge" className="rounded-full border border-amber-300/15 bg-amber-300/[0.08] px-2 py-0.5 text-[9px] text-amber-200">
                {message.badge}
              </span>
            )}
            {isLastAssistant && (
              <button
                type="button"
                onClick={onRegenerate}
                disabled={isBusy}
                aria-label={isRegenerating ? 'Regenerating...' : 'Regenerate response'}
                title={isRegenerating ? 'Regenerating...' : 'Regenerate response'}
                className="inline-flex items-center gap-1 text-[9px] text-slate-600 hover:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRegenerating ? (
                  <Loader2 size={11} className="animate-spin" />
                ) : (
                  <RotateCcw size={11} />
                )}
                {isRegenerating ? 'Regenerating...' : 'Regenerate'}
              </button>
            )}
            <button
              type="button"
              aria-label="Copy response"
              title="Copy"
              onClick={() => void navigator.clipboard?.writeText(message.content)}
              className="inline-flex items-center gap-1 text-[9px] text-slate-600 hover:text-slate-300"
            >
              <Copy size={11} />Copy
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
