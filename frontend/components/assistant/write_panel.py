import textwrap

content = textwrap.dedent('''\
'use client';

import { Maximize2, Minimize2, Plus, Send, X, Copy, RotateCcw, ChevronDown, ChevronUp, ToggleLeft, ToggleRight, Sparkles, AlertTriangle, Info, Loader2 } from 'lucide-react';
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
  onConversationChange: (messages: AssistantMessageRecord[]) => void;
  onNewConversation: () => void;
  onSendMessage: (message: string) => void;
  onRegenerate: () => void;
  onTogglePageContext: () => void;
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
''')

with open('AssistantPanel.tsx', 'w') as f:
    f.write(content)
print('Part 1 done')