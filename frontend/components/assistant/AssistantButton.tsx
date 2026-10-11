'use client';

import { Bot } from 'lucide-react';

interface AssistantButtonProps {
  onClick: () => void;
}

export function AssistantButton({ onClick }: AssistantButtonProps) {
  return (
    <button
      type="button"
      data-testid="assistant-button"
      aria-label="Ask Policy Assistant"
      title="Ask Policy Assistant"
      onClick={onClick}
      className="fixed bottom-6 right-6 z-[60] grid h-14 w-14 place-items-center rounded-full border border-cyan-300/30 bg-[#0b1930]/90 text-cyan-200 shadow-[0_0_24px_rgba(59,130,246,0.2),0_10px_30px_rgba(0,0,0,0.32)] backdrop-blur-xl transition duration-200 hover:border-violet-300/50 hover:bg-[#112344] hover:text-white focus:outline-none focus:ring-2 focus:ring-cyan-300/50 focus:ring-offset-2 focus:ring-offset-[#050b18]"
    >
      <Bot size={23} strokeWidth={1.8} />
    </button>
  );
}
