'use client';

import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { ConfidenceMeter } from './ConfidenceMeter';
import { PolicyScorecard } from './PolicyScorecard';
import type { MacroSignal, PolicyScorecardItem } from '@/lib/types';

interface DashboardPolicyIntelligenceProps {
  scorecard: PolicyScorecardItem[];
  signals: MacroSignal[];
}

export function DashboardPolicyIntelligence({ scorecard, signals }: DashboardPolicyIntelligenceProps) {
  if (scorecard.length === 0) {
    return (
      <section className="relative overflow-hidden rounded-[18px] border border-violet-300/15 bg-[rgba(15,23,42,0.66)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.25)] backdrop-blur-2xl">
        <p className="text-base font-semibold text-slate-50">Policy Intelligence</p>
        <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-300">Validated evidence required</p>
        <p className="mt-6 rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 text-xs leading-5 text-slate-400">
          No evidence-weighted policy scorecard is available for the connected data yet. This panel will not display a fabricated recommendation.
        </p>
      </section>
    );
  }
  const confidence = Math.round(scorecard.reduce((sum, item) => sum + item.score, 0) / Math.max(scorecard.length, 1));
  const chips = signals.slice(0, 3);

  return (
    <section className="relative overflow-hidden rounded-[18px] border border-violet-300/15 bg-[rgba(15,23,42,0.66)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.25),0_0_30px_rgba(139,92,246,0.06)] backdrop-blur-2xl">
      <span className="pointer-events-none absolute -right-16 -top-20 h-48 w-48 rounded-full bg-violet-500/10 blur-3xl" />
      <span className="pointer-events-none absolute bottom-0 left-1/3 h-32 w-48 rounded-full bg-blue-500/[0.07] blur-3xl" />
      <div className="relative flex items-start justify-between gap-4">
        <div><p className="text-base font-semibold text-slate-50">Policy Intelligence</p><p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-300">Research prototype</p></div>
        <CheckCircle2 size={17} className="text-violet-300" />
      </div>
      <div className="relative mt-6"><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Mock recommendation</p><h3 className="mt-2 text-xl font-bold tracking-tight text-slate-50">Maintain current stance</h3><div className="mt-4 max-w-xs"><div className="mb-2 flex items-center justify-between text-xs"><span className="text-slate-400">Confidence</span><strong className="tabular-nums text-slate-100">{confidence}%</strong></div><ConfidenceMeter value={confidence} /></div></div>
      <div className="relative mt-5 flex flex-wrap gap-2">{chips.map((signal) => <span key={signal.id} className="rounded-full border border-white/[0.08] bg-white/[0.045] px-2.5 py-1.5 text-[10px] font-medium text-slate-300">{signal.direction === 'up' ? '↑' : signal.direction === 'down' ? '↓' : '●'} {signal.label}</span>)}</div>
      <div className="relative mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3"><PolicyScorecard items={scorecard} overallScore={confidence} /></div>
      <button type="button" className="relative mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-violet-300 transition hover:text-violet-200">View Policy Analysis <ArrowRight size={13} /></button>
      <p className="relative mt-5 border-t border-white/[0.07] pt-3 text-[10px] leading-4 text-amber-300/80">Prototype scenario analysis.<br />Not an official RBI policy recommendation.</p>
    </section>
  );
}
