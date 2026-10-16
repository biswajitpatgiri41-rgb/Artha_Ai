'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Globe2, Landmark, TrendingUp } from 'lucide-react';
import { DashboardPolicyIntelligence, KPIGrid, MacroChart, ScenarioLab } from '@/components';
import { AgentTimeline, InflationDecomposition } from '@/components';
import { PageShell } from '@/components/layout';
import { loadOverviewData, type OverviewData } from '@/lib/overview-data';

export default function HomePage() {
  const [activeDomain, setActiveDomain] = useState('Inflation');
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { loadOverviewData().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Live data is unavailable')); }, []);
  const tabs = [
    { label: 'Inflation', icon: BarChart3, value: data?.kpis[0]?.value ?? 'Loading' },
    { label: 'Growth', icon: TrendingUp, value: data?.kpis[3]?.value ?? 'Loading' },
    { label: 'Rates', icon: Landmark, value: data?.kpis[2]?.value ?? 'Loading' },
    { label: 'External Sector', icon: Globe2, value: data?.kpis[4]?.value ?? 'Loading' },
  ];
  const empty = { scorecard: [], signals: [] };

  return (
    <PageShell
      title="Monetary policy overview"
      description="Track inflation, growth, monetary conditions and external risks through a unified research workspace."
      wide
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-1.5 rounded-2xl border border-white/[0.08] bg-white/[0.035] p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)] backdrop-blur-xl" role="tablist" aria-label="Research domains">
          {tabs.map((tab) => { const Icon = tab.icon; const isActive = activeDomain === tab.label; return <button key={tab.label} type="button" role="tab" aria-selected={isActive} onClick={() => setActiveDomain(tab.label)} className={`flex min-w-[132px] flex-1 items-center gap-2 rounded-xl border px-3 py-2 text-left transition duration-200 ${isActive ? 'border-blue-300/20 bg-blue-500/15 text-white shadow-[0_0_18px_rgba(59,130,246,0.08)]' : 'border-transparent text-slate-400 hover:bg-white/[0.045] hover:text-slate-100'}`}><Icon size={15} className={isActive ? 'text-cyan-300' : 'text-slate-500'} /><span><span className="block text-xs font-semibold">{tab.label}</span><span className="block text-[10px] opacity-70">{tab.value}</span></span></button>; })}
          <span className="hidden px-2 text-[9px] uppercase tracking-[0.12em] text-slate-600 xl:block">{activeDomain} · live</span>
        </div>
        {error && <p className="rounded-xl border border-rose-300/20 bg-rose-400/10 px-4 py-3 text-xs text-rose-200">Live data could not be loaded: {error}</p>}
        <KPIGrid items={data?.kpis ?? []} />
        <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
          <MacroChart observations={[]} historical={data?.historical ?? []} forecast={data?.forecast ?? []} isLoading={!data && !error} />
          <InflationDecomposition items={[]} isLoading={!data && !error} />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <ScenarioLab baselineInflation={data?.headline?.value} baselineDate={data?.headline?.date} />
          <DashboardPolicyIntelligence scorecard={empty.scorecard} signals={empty.signals} />
        </div>
        <AgentTimeline events={[]} />
      </div>
    </PageShell>
  );
}
