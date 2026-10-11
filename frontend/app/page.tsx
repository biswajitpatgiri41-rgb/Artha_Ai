'use client';

import { useState } from 'react';
import { BarChart3, Globe2, Landmark, TrendingUp } from 'lucide-react';
import { DashboardPolicyIntelligence, KPIGrid, MacroChart, ScenarioLab, RecentMacroSignals } from '@/components';
import { AgentTimeline, InflationDecomposition } from '@/components';
import { PageShell } from '@/components/layout';
import {
  mockAgentExecutionEvents,
  mockCpiForecast,
  mockCpiHistoricalTimeSeries,
  mockCpiInflation,
  mockGdpGrowth,
  mockInrUsd,
  mockInflationDecomposition,
  mockDashboardKpis,
  mockMacroObservations,
  mockMacroSignals,
  mockPolicyScorecard,
  mockRepoRate,
} from '@/lib/mock-data';

const domainTabs = [
  { label: 'Inflation', icon: BarChart3, value: `${mockCpiInflation.value.toFixed(1)}% CPI` },
  { label: 'Growth', icon: TrendingUp, value: `${mockGdpGrowth.value.toFixed(1)}% GDP` },
  { label: 'Rates', icon: Landmark, value: `${mockRepoRate.value.toFixed(2)}% repo` },
  { label: 'External Sector', icon: Globe2, value: `${mockInrUsd.value.toFixed(1)} INR/USD` },
];

export default function HomePage() {
  const [activeDomain, setActiveDomain] = useState('Inflation');

  return (
    <PageShell
      title="Monetary policy overview"
      description="Track inflation, growth, monetary conditions and external risks through a unified research workspace."
      wide
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-1.5 rounded-2xl border border-white/[0.08] bg-white/[0.035] p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)] backdrop-blur-xl" role="tablist" aria-label="Research domains">
          {domainTabs.map((tab) => { const Icon = tab.icon; const isActive = activeDomain === tab.label; return <button key={tab.label} type="button" role="tab" aria-selected={isActive} onClick={() => setActiveDomain(tab.label)} className={`flex min-w-[132px] flex-1 items-center gap-2 rounded-xl border px-3 py-2 text-left transition duration-200 ${isActive ? 'border-blue-300/20 bg-blue-500/15 text-white shadow-[0_0_18px_rgba(59,130,246,0.08)]' : 'border-transparent text-slate-400 hover:bg-white/[0.045] hover:text-slate-100'}`}><Icon size={15} className={isActive ? 'text-cyan-300' : 'text-slate-500'} /><span><span className="block text-xs font-semibold">{tab.label}</span><span className="block text-[10px] opacity-70">{tab.value}</span></span></button>; })}
          <span className="hidden px-2 text-[9px] uppercase tracking-[0.12em] text-slate-600 xl:block">{activeDomain} · demo</span>
        </div>
        <KPIGrid items={mockDashboardKpis} />
        <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
          <MacroChart observations={mockMacroObservations} historical={mockCpiHistoricalTimeSeries} forecast={mockCpiForecast} />
          <InflationDecomposition items={mockInflationDecomposition} />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <ScenarioLab />
          <DashboardPolicyIntelligence scorecard={mockPolicyScorecard} signals={mockMacroSignals} />
        </div>
        <div className="grid gap-5 xl:grid-cols-[1fr_1.15fr]">
          <RecentMacroSignals />
          <AgentTimeline events={mockAgentExecutionEvents} />
        </div>
      </div>
    </PageShell>
  );
}
