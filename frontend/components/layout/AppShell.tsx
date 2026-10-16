'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  BarChart3,
  BrainCircuit,
  BookOpen,
  ChevronRight,
  Database,
  FileSearch,
  GitCompareArrows,
  FileText,
  Gauge,
  Home,
  Landmark,
  LineChart,
  Menu,
  Network,
  ShieldCheck,
  Activity,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { navigationItems } from '@/lib/mock-data';
import { AssistantProvider } from '@/components/assistant/AssistantProvider';

const iconMap: Record<string, LucideIcon> = {
  Overview: Home,
  Analysis: BarChart3,
  Forecasts: LineChart,
  Simulator: SlidersHorizontal,
  Policy: Gauge,
  Data: Database,
  Logs: BookOpen,
  Reports: FileText,
  Architecture: Network,
  Evidence: FileSearch,
  Regimes: Activity,
  'Data Quality': ShieldCheck,
  'Model Registry': GitCompareArrows,
  'Knowledge Graph': Network,
  'Agent Evaluation': BrainCircuit,
};

const displayLabels: Record<string, string> = {
  Overview: 'Home',
  Analysis: 'Inflation Analysis',
  Forecasts: 'Forecasts',
  Simulator: 'Scenario Simulator',
  Policy: 'Policy Recommendations',
  Data: 'Data Explorer',
  Logs: 'Agent Logs',
  Reports: 'Reports',
  Architecture: 'System Architecture',
  Evidence: 'Evidence Workspace',
  Regimes: 'Regime Detection',
  'Data Quality': 'Data Quality Monitor',
  'Model Registry': 'Model Registry',
  'Knowledge Graph': 'Economic Knowledge Graph',
  'Agent Evaluation': 'Agent Evaluation',
};

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
    const heartbeat = () => {
      if (document.visibilityState !== 'visible') return;
      void fetch(`${apiBase}/visitor-heartbeat`, { cache: 'no-store', mode: 'cors' }).catch(() => undefined);
    };
    heartbeat();
    const interval = window.setInterval(heartbeat, 30_000);
    document.addEventListener('visibilitychange', heartbeat);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', heartbeat);
    };
  }, []);

  const closeMobileNav = () => setIsMobileNavOpen(false);

  return (
    <div className="min-h-screen bg-[#050B18] text-slate-50">
      <button
        type="button"
        aria-label="Open navigation"
        className="fixed left-4 top-4 z-40 rounded-lg border border-white/10 bg-[#0B1930]/90 p-2 text-slate-200 shadow-sm backdrop-blur-xl lg:hidden"
        onClick={() => setIsMobileNavOpen(true)}
      >
        <Menu size={20} strokeWidth={1.8} />
      </button>

      {isMobileNavOpen && (
        <button
          type="button"
          aria-label="Close navigation overlay"
          className="fixed inset-0 z-40 bg-slate-950/45 lg:hidden"
          onClick={closeMobileNav}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[245px] flex-col border-r border-white/[0.08] bg-[linear-gradient(180deg,rgba(11,25,48,0.94)_0%,rgba(5,11,24,0.97)_62%,rgba(7,20,38,0.96)_100%)] text-slate-300 shadow-2xl backdrop-blur-xl transition-transform duration-200 lg:translate-x-0 lg:shadow-none ${
          isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-start justify-between border-b border-white/[0.07] px-5 py-6">
          <Link href="/" className="flex items-center gap-3" onClick={closeMobileNav}>
            <span className="grid h-9 w-9 place-items-center rounded-xl border border-cyan-300/20 bg-blue-500/15 text-blue-300 shadow-lg shadow-blue-950/30">
              <Landmark size={19} strokeWidth={1.8} />
            </span>
            <span>
              <span className="block text-[13px] font-semibold tracking-wide text-slate-50">Monetary Intelligence</span>
              <span className="mt-1 block text-[9px] uppercase tracking-[0.15em] text-slate-500">India policy research</span>
            </span>
          </Link>
          <button
            type="button"
            aria-label="Close navigation"
            className="rounded-md p-1 text-slate-500 hover:bg-white/10 hover:text-white lg:hidden"
            onClick={closeMobileNav}
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-3 pt-7">
          <p className="mb-3 px-3 text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-600">Research workspace</p>
          <nav aria-label="Primary navigation" className="space-y-1">
            {navigationItems.map((item) => {
              const Icon = iconMap[item.label];
              const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={closeMobileNav}
                  className={`group flex items-center gap-3 rounded-xl border px-3 py-2.5 text-[13px] transition-colors ${
                    isActive
                      ? 'border-cyan-300/20 bg-blue-500/15 text-white shadow-[0_0_18px_rgba(59,130,246,0.08)]'
                      : 'border-transparent text-slate-400 hover:bg-white/[0.045] hover:text-slate-100'
                  }`}
                >
                  <Icon size={17} strokeWidth={isActive ? 2.2 : 1.8} className={isActive ? 'text-blue-300' : 'text-slate-500 group-hover:text-slate-300'} />
                  <span className="flex-1">{displayLabels[item.label]}</span>
                  {isActive && <ChevronRight size={14} className="text-blue-300" />}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-auto px-3 pb-5">
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)]">
            <div className="flex items-center gap-2 text-[11px] font-medium text-slate-200">
              <ShieldCheck size={14} className="text-slate-400" />
              Research Environment
            </div>
            <div className="mt-3 flex items-center gap-2 text-[10px] font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              API-backed research
            </div>
            <p className="mt-2 text-[10px] text-slate-500">Page status reflects configured capabilities</p>
          </div>
          <p className="mt-4 px-1 text-[10px] text-slate-600">v0.1 · RBI policy lab</p>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-[245px]">
        <div className="flex min-h-14 items-center justify-end border-b border-white/[0.08] bg-[#071426]/60 px-6 backdrop-blur-xl sm:px-8">
          <div className="flex items-center gap-3 text-right">
            <div className="hidden items-center gap-2 sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.55)]" />
              <span className="rounded-full border border-cyan-400/15 bg-cyan-400/10 px-2.5 py-1 text-[10px] font-semibold text-cyan-200">Research workspace</span>
            </div>
            <div>
              <p className="text-[9px] uppercase tracking-[0.16em] text-slate-600">Last updated</p>
              <p className="mt-0.5 text-[11px] font-medium text-slate-300">Live API</p>
            </div>
          </div>
        </div>
        <AssistantProvider>{children}</AssistantProvider>
      </div>
    </div>
  );
}
