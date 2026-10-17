'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Globe2, Landmark, TrendingUp } from 'lucide-react';
import { DashboardPolicyIntelligence, KPIGrid, MacroChart, ScenarioLab } from '@/components';
import { AgentTimeline, InflationDecomposition } from '@/components';
import { PageShell } from '@/components/layout';
import { loadOverviewData, type OverviewData } from '@/lib/overview-data';
import { getResearchRuns } from '@/lib/research-api';
import type { AgentExecutionEvent } from '@/lib/types';

export default function HomePage() {
  const [activeDomain, setActiveDomain] = useState('Inflation');
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activity, setActivity] = useState<AgentExecutionEvent[]>([]);
  useEffect(() => {
    loadOverviewData().then((overview) => {
      setData(overview);
      const timestamp = new Date().toISOString();
      const observedCount = overview.kpis.filter((item) => item.observation).length;
      const loadedEvents: AgentExecutionEvent[] = [{
        id: `homepage-data-${timestamp}`,
        timestamp,
        agent: 'Data API',
        event: 'Macro observations loaded',
        status: observedCount ? 'completed' : 'warning',
        details: `${observedCount} of ${overview.kpis.length} dashboard indicators returned a dated observation${overview.latestDate ? `; latest CPI observation is ${overview.latestDate}` : ''}.`,
        toolCalls: ['/series/{series_id}'],
      }];
      if (overview.forecast.length) loadedEvents.push({
        id: `homepage-forecast-${timestamp}`,
        timestamp,
        agent: 'Forecast API',
        event: 'CPI forecast retrieved',
        status: 'completed',
        details: `Retrieved ${overview.forecast.length} stored forecast points from the project API.`,
        toolCalls: ['/forecast?series_id=cpi_yoy'],
      });
      setActivity(loadedEvents);
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Live data is unavailable'));

    getResearchRuns().then((runs) => {
      const runEvents: AgentExecutionEvent[] = runs.flatMap((run) => run.events.map((event, index) => ({
        id: `${run.run_id}-${event.node_id}-${index}`,
        timestamp: event.timestamp || run.created_at,
        agent: `Research run ${run.run_id.slice(0, 8)}`,
        event: event.node_id,
        status: event.status === 'completed' || event.status === 'warning' || event.status === 'failed' || event.status === 'running' || event.status === 'queued' ? event.status : 'pending',
        details: event.message,
        toolCalls: [],
      })));
      if (runEvents.length) setActivity((current) => [...runEvents, ...current].sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp)).slice(0, 8));
    }).catch(() => {
      // The API health and homepage data activity remain visible when run history is unavailable.
    });
  }, []);
  const tabs = [
    { label: 'Inflation', icon: BarChart3, value: data?.kpis[0]?.value ?? 'Loading' },
    { label: 'Growth', icon: TrendingUp, value: data?.kpis[3]?.value ?? 'Loading' },
    { label: 'Rates', icon: Landmark, value: data?.kpis[2]?.value ?? 'Loading' },
    { label: 'External Sector', icon: Globe2, value: data?.kpis[4]?.value ?? 'Loading' },
  ];
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
        <div className="grid items-start gap-6 lg:grid-cols-2">
          <ScenarioLab baselineInflation={data?.headline?.value} baselineDate={data?.headline?.date} />
          <DashboardPolicyIntelligence indicators={data?.kpis ?? []} forecast={data?.forecast ?? []} />
        </div>
        <AgentTimeline events={activity} />
      </div>
    </PageShell>
  );
}
