import { ArchitectureGraph } from '@/components/architecture';
import { PageShell } from '@/components/layout';

export default function ArchitecturePage() {
  return <PageShell title="System Architecture" description="Production data, numerical forecasting, scenario analysis, agent orchestration, and run-scoped evidence." wide><div className="space-y-5"><div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cyan-300/10 bg-cyan-400/[0.035] px-4 py-3 text-xs text-slate-400"><span>Deterministic forecasts stay separate from NVIDIA powered agents and document retrieval.</span><span className="rounded-full border border-amber-300/15 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-amber-200">Demo + runtime evidence events</span></div><ArchitectureGraph /></div></PageShell>;
}
