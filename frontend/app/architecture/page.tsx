import { ArchitectureGraph } from '@/components/architecture';
import { PageShell } from '@/components/layout';

export default function ArchitecturePage() {
  return <PageShell title="System Architecture" description="Live data ingestion, validated numerical forecasting, evidence checks, API delivery, and connected research pages." wide><div className="space-y-5"><div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cyan-300/10 bg-cyan-400/[0.035] px-4 py-3 text-xs text-slate-400"><span>The highlighted path follows the connected runtime: sources → validation → forecast → evaluation → API → research terminal.</span><span className="rounded-full border border-emerald-300/15 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-emerald-200">Runtime flow</span></div><ArchitectureGraph /></div></PageShell>;
}
