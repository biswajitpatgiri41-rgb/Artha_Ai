'use client';

import { ArrowRight, ChevronUp, Flame, Globe2, TrendingUp, Banknote, Zap, Waves, Database } from 'lucide-react';
import { mockMacroSignals, mockFoodInflation, mockGdpGrowth, mockInrUsd, mockRepoRate, mockSeriesCatalog, mockSources } from '@/lib/mock-data';
import type { MacroSignal } from '@/lib/types';

const macroPulseItems = [
  { key: 'inflation', label: 'INFLATION', icon: Flame, color: 'text-amber-400', bg: 'bg-amber-500/[0.06]', border: 'border-amber-400/15', status: 'Elevated', direction: 'up' as const, detail: 'Food pressure dominant', value: `${mockFoodInflation.value.toFixed(1)}% food CPI` },
  { key: 'growth', label: 'GROWTH', icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/[0.06]', border: 'border-emerald-400/15', status: 'Resilient', direction: 'right' as const, detail: 'Domestic demand stable', value: `${mockGdpGrowth.value.toFixed(1)}% GDP` },
  { key: 'fx', label: 'FX', icon: Globe2, color: 'text-cyan-400', bg: 'bg-cyan-500/[0.06]', border: 'border-cyan-400/15', status: 'Watch', direction: 'right' as const, detail: 'INR range-bound', value: `${mockInrUsd.value.toFixed(1)} INR/USD` },
  { key: 'energy', label: 'ENERGY', icon: Zap, color: 'text-rose-400', bg: 'bg-rose-500/[0.06]', border: 'border-rose-400/15', status: 'Pressure', direction: 'up' as const, detail: 'Crude above 75', value: `$${mockSeriesCatalog.find(s => s.id === 'brent-crude')?.latestValue.toFixed(1)}/bbl` },
  { key: 'policy', label: 'POLICY', icon: Banknote, color: 'text-violet-400', bg: 'bg-violet-500/[0.06]', border: 'border-violet-400/15', status: 'Stable', direction: 'right' as const, detail: 'Repo unchanged', value: `${mockRepoRate.value.toFixed(2)}% repo` },
  { key: 'external', label: 'EXTERNAL', icon: Waves, color: 'text-blue-400', bg: 'bg-blue-500/[0.06]', border: 'border-blue-400/15', status: 'Moderate', direction: 'right' as const, detail: 'Fed easing path', value: `${mockSeriesCatalog.find(s => s.id === 'us-fed-rate')?.latestValue.toFixed(2)}% fed` },
];

const riskWatchItems = [
  { label: 'Food Prices', severity: 'HIGH' as const, intensity: 85, color: 'bg-amber-400', detail: 'Persistence risk', source: mockFoodInflation },
  { label: 'Energy / Crude', severity: 'MODERATE' as const, intensity: 60, color: 'bg-rose-400', detail: 'Geopolitical sensitivity', source: mockSeriesCatalog.find(s => s.id === 'brent-crude')! },
  { label: 'Currency / External', severity: 'WATCH' as const, intensity: 45, color: 'bg-cyan-400', detail: 'Fed/INR dynamics', source: mockInrUsd },
];

const watchlistItems = [
  { key: 'food-persistence', label: 'Food inflation persistence', status: 'Elevated' as const, color: 'text-rose-400', dot: 'bg-rose-400', detail: 'Above 5% YoY' },
  { key: 'brent-crude', label: 'Brent crude movement', status: 'Monitor' as const, color: 'text-amber-400', dot: 'bg-amber-400', detail: 'Volatile range' },
  { key: 'inr-depreciation', label: 'INR depreciation pressure', status: 'Stable' as const, color: 'text-emerald-400', dot: 'bg-emerald-400', detail: 'Within range' },
  { key: 'policy-transmission', label: 'Policy-rate transmission', status: 'Unchanged' as const, color: 'text-slate-400', dot: 'bg-slate-400', detail: 'Repo at 6.50%' },
];

function DirectionIcon({ direction, color }: { direction: 'up' | 'down' | 'right'; color: string }) {
  if (direction === 'up') return <ChevronUp size={10} className={color} />;
  if (direction === 'down') return <ChevronUp size={10} className={`${color} rotate-180`} />;
  return <ArrowRight size={10} className={color} />;
}

function RiskBar({ intensity, color }: { intensity: number; color: string }) {
  return (
    <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
      <div className={`h-full rounded-full ${color}`} style={{
        width: `${intensity}%`,
        transition: 'width 0.4s ease-out',
      }} />
    </div>
  );
}

function SeverityBadge({ severity }: { severity: 'HIGH' | 'MODERATE' | 'WATCH' }) {
  const configs = {
    HIGH: { bg: 'bg-rose-400/10', text: 'text-rose-300', border: 'border-rose-400/20' },
    MODERATE: { bg: 'bg-amber-400/10', text: 'text-amber-300', border: 'border-amber-400/20' },
    WATCH: { bg: 'bg-cyan-400/10', text: 'text-cyan-300', border: 'border-cyan-400/20' },
  };
  const cfg = configs[severity];
  return <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase ${cfg.bg} ${cfg.text} ${cfg.border}`}>{severity}</span>;
}

export function RecentMacroSignals() {
  return (
    <section className="relative h-full min-h-[420px] overflow-hidden rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.68)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.24)] backdrop-blur-2xl">
      {/* Header */}
      <div className="relative flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-100">Recent macro signals</h2>
          <p className="mt-1 text-xs text-slate-400">Signals flagged by the demo research workspace</p>
        </div>
        <span className="rounded-md border border-white/[0.08] bg-white/[0.035] px-2 py-1 text-[10px] font-semibold text-slate-400">{mockMacroSignals.length} signals</span>
      </div>

      {/* Existing 3 Macro Signals */}
      <div className="relative mt-5 space-y-4">
        {mockMacroSignals.map((signal: MacroSignal) => (
          <div key={signal.id} className="flex items-start gap-3 border-t border-white/[0.08] pt-3">
            <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${signal.severity === 'medium' ? 'bg-amber-500' : signal.severity === 'high' ? 'bg-rose-500' : 'bg-emerald-500'}`} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold text-slate-200">{signal.label}</p>
                <span className="text-[10px] uppercase tracking-[0.1em] text-slate-500">{signal.observation.value} {signal.observation.unit}</span>
              </div>
              <p className="mt-1 text-[11px] leading-5 text-slate-400">{signal.summary}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Section 1: Macro Pulse */}
      <div className="relative mt-6 border-t border-white/[0.08] pt-5">
        <h3 className="text-xs font-semibold text-slate-400 mb-3">Macro Pulse</h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {macroPulseItems.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.key} className={`rounded-xl border ${item.border} ${item.bg} p-3 transition hover:border-opacity-70 hover:bg-opacity-100`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Icon size={13} className={item.color} />
                    <span className="text-[9px] font-semibold tracking-[0.1em] text-slate-400 uppercase">{item.label}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <DirectionIcon direction={item.direction} color={item.color} />
                    <span className={`text-[10px] font-medium ${item.color}`}>{item.status}</span>
                  </div>
                </div>
                <p className="mt-1.5 text-[10px] font-medium text-slate-300">{item.detail}</p>
                <p className="mt-0.5 text-[9px] text-slate-500">{item.value}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Section 2: Risk Watch */}
      <div className="relative mt-6 border-t border-white/[0.08] pt-5">
        <h3 className="text-xs font-semibold text-slate-400 mb-3">Risk Watch</h3>
        <div className="space-y-3">
          {riskWatchItems.map((item) => (
            <div key={item.label} className="flex items-center gap-3">
              <span className="w-28 text-[10px] font-medium text-slate-300">{item.label}</span>
              <SeverityBadge severity={item.severity} />
              <div className="flex-1 mr-2">
                <RiskBar intensity={item.intensity} color={item.color} />
              </div>
              <span className="w-36 text-right text-[9px] text-slate-500">{item.detail}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Economic Watchlist */}
      <div className="relative mt-6 border-t border-white/[0.08] pt-5">
        <h3 className="text-xs font-semibold text-slate-400 mb-3">Economic Watchlist</h3>
        <div className="space-y-2">
          {watchlistItems.map((item) => (
            <div key={item.key} className="flex items-center gap-3">
              <span className={`h-2 w-2 shrink-0 rounded-full ${item.dot}`} />
              <span className="flex-1 text-[10px] font-medium text-slate-200">{item.label}</span>
              <span className={`text-[9px] font-medium ${item.color} px-1.5 py-0.5 rounded bg-white/[0.05]`}>{item.status}</span>
              <span className="text-[9px] text-slate-500">{item.detail}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 4: Data Status Footer */}
      <div className="relative mt-6 border-t border-white/[0.08] pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[10px] text-slate-500">Research signals \u00b7 Demo/Mock context</p>
          <div className="flex items-center gap-2">
            <Database size={10} className="text-slate-500" />
            <span className="text-[9px] text-slate-500">Sources:</span>
            <span className="text-[9px] font-medium text-slate-400">
              {mockSources.filter(s => ['mospi', 'rbi-dbie', 'eia', 'fred'].includes(s.id)).map(s => s.name).join(' \u00b7 ')}
            </span>
            <span className="text-[9px] text-slate-600">(mock)</span>
          </div>
        </div>
      </div>
    </section>
  );
}
