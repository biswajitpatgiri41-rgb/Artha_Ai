'use client';

import { Maximize2, Minimize2, Plus, Send, X, Copy, RotateCcw, ChevronDown, ChevronUp, ToggleLeft, ToggleRight, Sparkles, AlertTriangle, Info, Loader2, FileText, Sparkles as SparklesIcon } from 'lucide-react';
import { useRef, useEffect, useState, useCallback } from 'react';
import type { AssistantPageContext } from '@/lib/assistant-context';
import type { AssistantMessageRecord, AssistantState } from '@/lib/assistant-types';
import { AssistantMessage } from './AssistantMessage';

interface AssistantPanelProps {
  context: AssistantPageContext;
  pageData: import('@/lib/assistant-context').PageAssistantContext;
  messages: AssistantMessageRecord[];
  state: AssistantState;
  error: string | null;
  contextNotice: string | null;
  pageContextEnabled: boolean;
  evidenceEnabled: boolean;
  onConversationChange: (messages: AssistantMessageRecord[]) => void;
  onNewConversation: () => void;
  onSendMessage: (message: string) => void;
  onRegenerate: () => void;
  onTogglePageContext: () => void;
  onToggleEvidence: () => void;
  isMinimized: boolean;
  onClose: () => void;
  onMinimize: () => void;
}
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2.5">
      <span className="flex items-center gap-1 text-slate-500">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" />
      </span>
    </div>
  );
}

function ContextBadge({ context, pageData, pageContextEnabled, onToggle, evidenceEnabled, onToggleEvidence }: {
  context: AssistantPageContext;
  pageData: import('@/lib/assistant-context').PageAssistantContext;
  pageContextEnabled: boolean;
  onToggle: () => void;
  evidenceEnabled: boolean;
  onToggleEvidence: () => void;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-300/30 bg-cyan-300/[0.08] px-2.5 py-1 text-[10px] font-medium text-cyan-200">
        <span className="h-1.5 w-1.5 rounded-full bg-cyan-300" />
        {context.title}
      </span>
      {pageData.visibleMetrics.length > 0 && (
        <span className="text-[10px] text-slate-500">Using context from this page</span>
      )}
      <button
        type="button"
        onClick={onToggle}
        aria-label={pageContextEnabled ? 'Disable page context' : 'Enable page context'}
        className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] text-slate-400 hover:bg-white/10 hover:text-slate-200 transition"
      >
        {pageContextEnabled ? (
          <>
            <ToggleRight size={12} /> Page context <span className="text-emerald-300">ON</span>
          </>
        ) : (
          <>
            <ToggleLeft size={12} /> Page context <span className="text-amber-300">OFF</span>
          </>
        )}
      </button>
      <button
        type="button"
        onClick={onToggleEvidence}
        aria-label={evidenceEnabled ? 'Disable evidence context' : 'Enable evidence context'}
        className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] text-slate-400 hover:bg-white/10 hover:text-slate-200 transition"
      >
        {evidenceEnabled ? (
          <>
            <FileText size={12} /> Evidence <span className="text-emerald-300">ON</span>
          </>
        ) : (
          <>
            <FileText size={12} /> Evidence <span className="text-amber-300">OFF</span>
          </>
        )}
      </button>
    </div>
  );
}

export function AssistantPanel({
  context,
  pageData,
  messages,
  state,
  error,
  contextNotice,
  pageContextEnabled,
  evidenceEnabled,
  onConversationChange,
  onNewConversation,
  onSendMessage,
  onRegenerate,
  onTogglePageContext,
  onToggleEvidence,
  isMinimized,
  onClose,
  onMinimize,
}: AssistantPanelProps) {
  const [message, setMessage] = useState('');
  const [inputHeight, setInputHeight] = useState(44);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const prevStateRef = useRef<AssistantState>('idle');

  // Return focus to textarea after request completes (success or recoverable error)
  // Only if panel is still open and user hasn't focused elsewhere
  useEffect(() => {
    const prevState = prevStateRef.current;
    prevStateRef.current = state;

    // Focus when transitioning FROM busy/error TO idle
    const wasBusy = prevState === 'sending' || prevState === 'receiving' || prevState === 'error';
    const nowIdle = state === 'idle';

    if (wasBusy && nowIdle && textareaRef.current) {
      // Small defer to allow state to settle and ensure panel is still mounted
      const timer = setTimeout(() => {
        if (textareaRef.current && document.activeElement !== textareaRef.current) {
          textareaRef.current.focus();
        }
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [state]);

  const adjustHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 160);
      setInputHeight(newHeight);
    }
  }, []);

  const handleSubmit = useCallback((event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!message.trim() || state !== 'idle') return;
    onSendMessage(message.trim());
    setMessage('');
    setInputHeight(44);
  }, [message, state, onSendMessage]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event as unknown as React.FormEvent<HTMLFormElement>);
    }
  }, [handleSubmit]);

  useEffect(() => {
    adjustHeight();
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, state, adjustHeight]);

  if (isMinimized) {
    return (
      <div className="fixed bottom-6 right-6 z-[60] flex items-center gap-2 rounded-full border border-white/10 bg-[#0b1930]/95 p-2 pl-4 text-xs text-slate-300 shadow-2xl backdrop-blur-xl">
        <span>Policy Assistant</span>
        <button type="button" aria-label="Restore Policy Assistant" title="Restore" onClick={onMinimize} className="rounded-full p-2 text-slate-400 hover:bg-white/10 hover:text-white">
          <Maximize2 size={15} />
        </button>
        <button type="button" aria-label="Close Policy Assistant" title="Close" onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-white/10 hover:text-white">
          <X size={15} />
        </button>
      </div>
    );
  }

  return (
  <section
    data-testid="assistant-panel"
    aria-label="Policy Research Assistant"
    className="fixed bottom-6 right-6 z-[60] flex h-[min(650px,80vh)] w-[min(410px,calc(100vw-2rem))] flex-col overflow-hidden rounded-[20px] border border-cyan-200/15 bg-[#08152a]/95 shadow-[0_0_42px_rgba(59,130,246,0.13),0_24px_60px_rgba(0,0,0,0.42)] backdrop-blur-2xl max-sm:bottom-3 max-sm:right-3 max-sm:h-[82vh] max-sm:w-[calc(100vw-1.5rem)]">
      <header className="border-b border-white/[0.08] px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-semibold text-slate-100">Policy Research Assistant</p>
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-medium ${
                state === 'error' ? 'border-amber-300/30 bg-amber-300/10 text-amber-300' :
                state === 'sending' || state === 'receiving' ? 'border-blue-300/30 bg-blue-300/10 text-blue-300' :
                'border-emerald-300/30 bg-emerald-300/10 text-emerald-300'
              }`}>
                {state === 'error' && <AlertTriangle size={10} />}
                {state === 'sending' && <Loader2 size={10} className="animate-spin" />}
                {state === 'receiving' && <Sparkles size={10} />}
                {(state === 'idle' || state === 'error') && <span className="h-1.5 w-1.5 rounded-full" />}
                {state === 'idle' ? 'Ready' : state === 'sending' ? 'Sending...' : state === 'receiving' ? 'Receiving...' : 'Error'}
              </span>
            </div>
            <ContextBadge context={context} pageData={pageData} pageContextEnabled={pageContextEnabled} onToggle={onTogglePageContext} evidenceEnabled={evidenceEnabled} onToggleEvidence={onToggleEvidence} />
          </div>
          <div className="flex items-center gap-1 text-slate-500">
            <button type="button" aria-label="New conversation" title="New conversation" onClick={onNewConversation} className="rounded-md p-1.5 hover:bg-white/10 hover:text-slate-200">
              <Plus size={16} />
            </button>
            <button type="button" aria-label="Minimize assistant" title="Minimize" onClick={onMinimize} className="rounded-md p-1.5 hover:bg-white/10 hover:text-slate-200">
              <Minimize2 size={16} />
            </button>
            <button type="button" aria-label="Close assistant" title="Close" onClick={onClose} className="rounded-md p-1.5 hover:bg-white/10 hover:text-slate-200">
              <X size={17} />
            </button>
          </div>
        </div>
        {contextNotice && (
          <div className="mt-3 rounded-lg border border-amber-300/20 bg-amber-300/5 px-3 py-2 text-[10px] text-amber-200 animate-fade-in">
            <Info size={11} className="inline-block mr-1" /> {contextNotice}
          </div>
        )}
        {error && (
          <div data-testid="assistant-error" className="mt-3 rounded-lg border border-red-300/20 bg-red-300/5 px-3 py-2 text-[10px] text-red-200 animate-fade-in">
            <AlertTriangle size={11} className="inline-block mr-1" /> {error}
          </div>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-500">
            <Sparkles size={32} className="mb-3 text-slate-600" />
            <p className="text-sm font-medium text-slate-400">Ask me anything about this page</p>
            <p className="mt-1 text-[11px] text-slate-600 max-w-[280px]">
              I can explain concepts, discuss hypothetical scenarios, and help you understand the data on this page.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 justify-center max-w-[280px]">
              {context.suggestions.slice(0, 3).map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSendMessage(suggestion)}
                  disabled={state !== 'idle'}
                  className="text-left rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-[10px] text-slate-400 hover:border-cyan-300/30 hover:bg-cyan-300/5 hover:text-slate-200 transition disabled:opacity-50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

{messages.map((msg) => (
          <AssistantMessage
            key={msg.id}
            message={msg}
            onRegenerate={msg.role === 'assistant' && messages[messages.length - 1]?.id === msg.id ? onRegenerate : undefined}
            isRegenerating={msg.isRegenerating}
            state={state}
          />
        ))}
        {(state === 'sending' || state === 'receiving') && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t border-white/[0.08] p-4">
        <div className="relative">
          <textarea
            ref={textareaRef}
            data-testid="assistant-input"
            value={message}
            onChange={(event) => { setMessage(event.target.value); adjustHeight(); }}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this page... (Enter to send, Shift+Enter for new line)"
            aria-label="Message Policy Assistant"
            disabled={state !== 'idle'}
            rows={1}
            className="w-full min-h-[44px] max-h-[160px] resize-none rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 pr-12 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-300/30 disabled:cursor-not-allowed disabled:opacity-50"
            style={{ height: inputHeight }}
          />
          <button
            type="submit"
            data-testid="assistant-send"
            aria-label="Send message"
            title="Send message"
            disabled={!message.trim() || state !== 'idle'}
            className="absolute right-2 bottom-2 grid h-8 w-8 place-items-center rounded-lg bg-blue-500/20 text-cyan-200 transition hover:bg-blue-500/35 disabled:cursor-not-allowed disabled:opacity-35"
          >
            <Send size={15} />
          </button>
        </div>
        <p className="mt-2 text-[10px] text-slate-600 text-center">
          Research copilot · Enter to send, Shift+Enter for new line
        </p>
      </form>
    </section>
  );
}
