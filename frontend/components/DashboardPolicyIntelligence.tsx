'use client';

import { Activity, ArrowUpRight, Database, Gauge } from 'lucide-react';
import type { EconomicObservation, ForecastPoint, Kpi } from '@/lib/types';

interface DashboardPolicyIntelligenceProps {
  indicators: Kpi[];
  forecast: ForecastPoint[];
}

function formatDate(value: string) {
  const date = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short' }).format(date);
}

function formatObservation(observation: EconomicObservation) {
  const suffix = observation.unit === '%' || observation.unit.toLowerCase().includes('percent') ? '%' : '';
  return `${observation.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

export function DashboardPolicyIntelligence({ indicators, forecast }: DashboardPolicyIntelligenceProps) {
  const available = indicators.flatMap((item) => item.observation ? [{ label: item.label, observation: item.observation }] : []);
  const forecastStart = forecast[0];
  const forecastEnd = forecast.at(-1);

  return (
    <section className="relative overflow-hidden rounded-[18px] border border-violet-300/15 bg-[rgba(15,23,42,0.66)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.25)] backdrop-blur-2xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-slate-50">Policy Intelligence</p>
          <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-300">Live evidence monitor</p>
        </div>
        <Activity size={17} className="text-violet-300" />
      </div>

      {available.length ? (
        <>
          <div className="mt-5 grid grid-cols-2 gap-2">
            {available.map(({ label, observation }) => (
              <div key={observation.id} className="min-w-0 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3">
                <p className="truncate text-[10px] font-medium text-slate-400">{label}</p>
                <p className="mt-1 text-lg font-semibold tabular-nums text-slate-100">{formatObservation(observation)}</p>
                <p className="mt-1 truncate text-[10px] text-slate-500">{formatDate(observation.date)} · {observation.source}</p>
              </div>
            ))}
          </div>

          {forecastStart && forecastEnd ? (
            <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-cyan-300/10 bg-cyan-400/[0.04] p-3">
              <div className="flex min-w-0 items-center gap-2"><Gauge size={15} className="shrink-0 text-cyan-300" /><div><p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-200">Stored CPI model path</p><p className="mt-0.5 text-[10px] text-slate-400">{formatDate(forecastStart.date)} to {formatDate(forecastEnd.date)}</p></div></div>
              <p className="shrink-0 text-sm font-semibold tabular-nums text-slate-100">{forecastStart.value.toFixed(2)}% <ArrowUpRight size={12} className="inline text-slate-500" /> {forecastEnd.value.toFixed(2)}%</p>
            </div>
          ) : null}

          <p className="mt-4 flex items-start gap-2 border-t border-white/[0.07] pt-3 text-[10px] leading-4 text-slate-400"><Database size={13} className="mt-0.5 shrink-0 text-slate-500" />Latest observations and the stored CPI forecast are shown as evidence. They do not constitute a policy recommendation or causal estimate.</p>
        </>
      ) : (
        <p className="mt-5 rounded-xl border border-amber-300/15 bg-amber-400/[0.05] p-4 text-xs leading-5 text-amber-100">The API returned no observed macro indicators. Check the data API connection and series availability.</p>
      )}
    </section>
  );
}
