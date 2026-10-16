import type { ReactNode } from 'react';

interface PageShellProps {
  title: string;
  description: string;
  children?: ReactNode;
  wide?: boolean;
}

export function PageShell({ title, description, children, wide = false }: PageShellProps) {
  return (
    <main className="min-h-[calc(100vh-4rem)] px-5 py-8 text-slate-50 sm:px-8 sm:py-10">
      <div className={`mx-auto w-full ${wide ? 'max-w-[1600px]' : 'max-w-7xl'}`}>
        <header className="relative mb-8 overflow-hidden border-b border-white/[0.08] pb-7 pt-2 md:flex md:items-end md:justify-between">
          <div className="pointer-events-none absolute -left-20 -top-24 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
          <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-cyan-400/[0.06] blur-3xl" />
          <div className="relative">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-cyan-300">India Macro Intelligence</p>
              <span className="rounded-full border border-emerald-300/15 bg-emerald-400/10 px-2 py-1 text-[9px] font-semibold text-emerald-200">Runtime data</span>
              <span className="rounded-full border border-white/[0.09] bg-white/[0.04] px-2 py-1 text-[9px] font-semibold text-slate-400">Research workspace</span>
            </div>
            <h1 className="text-[2rem] font-bold tracking-[-0.035em] text-slate-50 sm:text-[2.55rem]">{title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{description}</p>
          </div>
        </header>
        {children}
      </div>
    </main>
  );
}
