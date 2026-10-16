'use client';

import { useEffect, useState } from 'react';
import type { ForecastResponse, PackagedModelMetric, PackagedModelRegistry, ResearchRunResponse } from '@/lib/research-api';
import { getResearchRuns } from '@/lib/research-api';

const panel = 'rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.18)] backdrop-blur-2xl';
const status = 'rounded-full border border-amber-300/20 bg-amber-300/[0.06] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-200';

export interface ForecastCalibrationOutput { coverage_80: number | null; coverage_95: number | null; status: string; model_version: string; }
export interface ForecastExplanationOutput { model_version: string; method: 'shap' | 'feature_importance' | 'coefficients'; contributions: Array<{ feature: string; contribution: number; unit?: string }>; }
export interface ForecastVintageOutput { run_id: string; generated_at: string; data_vintage: string | null; model_version?: string; forecast: number | null; }

function Section({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return <section className={panel}><div className="mb-4"><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-300">Forecast intelligence</p><h2 className="mt-1 text-base font-semibold text-slate-50">{title}</h2><p className="mt-1 text-xs text-slate-400">{subtitle}</p></div>{children}</section>;
}

export function ModelEnsembleComparison({ registry, horizon, variant }: { registry: PackagedModelRegistry | null; horizon: number; variant?: string }) {
  const rows = registry?.metrics.filter((item) => item.horizon_months === horizon && (!variant || item.variant === variant)) ?? [];
  const present = new Set(rows.map((item) => item.model));
  const pendingRows = [
    ...(!present.has('seasonal_naive') ? ['Seasonal Naive'] : []),
    ...(!present.has('ets') ? ['ETS'] : []),
    ...(!present.has('arima') ? ['ARIMA'] : []),
    ...(!present.has('sarima') ? ['SARIMA'] : []),
    ...(!present.has('sarimax') ? ['SARIMAX'] : []),
    ...(!present.has('var') ? ['VAR'] : []),
    ...(!present.has('xgboost') ? ['XGBoost'] : []),
    ...(!present.has('ensemble') ? ['Ensemble'] : []),
  ];
  const coverage = (value: number | null | undefined) => value == null ? '?' : `${(value * 100).toFixed(1)}%`;
  return <Section title="Model ensemble comparison" subtitle="Metrics and weights are read from the selected final package; unavailable values stay blank.">
    <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-xs"><thead className="text-[10px] uppercase tracking-wide text-slate-500"><tr>{['Model', 'Horizon', 'Weight', 'MAE', 'RMSE', '80% / 95% coverage'].map((item) => <th key={item} className="px-3 py-2">{item}</th>)}</tr></thead><tbody>{rows.map((item: PackagedModelMetric) => <tr key={`${item.model}-${item.variant}`} className="border-t border-white/[0.06] text-slate-300"><td className="px-3 py-3">{item.model_label} ? {item.variant}</td><td className="px-3 py-3">{item.horizon_months} mo</td><td className="px-3 py-3">{item.model_weight == null ? '?' : item.model_weight.toFixed(3)}</td><td className="px-3 py-3">{item.mae_pp.toFixed(3)} pp</td><td className="px-3 py-3">{item.rmse_pp.toFixed(3)} pp</td><td className="px-3 py-3">{coverage(item.coverage_80)} / {coverage(item.coverage_95)}</td></tr>)}{pendingRows.map((label) => <tr key={`pending-${label}`} className="border-t border-white/[0.06] text-slate-500"><td className="px-3 py-3">{label}</td><td className="px-3 py-3">{horizon} mo</td><td className="px-3 py-3">?</td><td className="px-3 py-3">?</td><td className="px-3 py-3">?</td><td className="px-3 py-3">?</td></tr>)}</tbody></table></div>
    {!rows.length && <p className="text-sm text-slate-400">No registered model available for this horizon.</p>}
    <p className="mt-3 text-[11px] text-slate-500">Comparison-period interval coverage uses development-period calibration; it is not guaranteed future coverage.</p>
  </Section>;
}

export function ForecastExplainability({ explanation, forecast }: { explanation?: ForecastExplanationOutput | null; forecast?: ForecastResponse | null }) {
  const componentFacts = forecast?.component_forecasts ? Object.entries(forecast.component_forecasts) : [];
  return <Section title="Forecast explainability" subtitle="Feature contributions are supplied by validated model artifacts; this page does not calculate SHAP.">
    {explanation?.contributions?.length ? <div className="space-y-3">{explanation.contributions.map((item) => <div key={item.feature} className="grid grid-cols-[160px_1fr_auto] items-center gap-3 text-xs"><span className="text-slate-300">{item.feature}</span><div className="h-2 rounded-full bg-white/[0.06]"><div className="h-2 rounded-full bg-cyan-400" style={{ width: `${Math.min(100, Math.abs(item.contribution) * 10)}%` }} /></div><span className="text-slate-400">{item.contribution.toFixed(3)} {item.unit ?? ''}</span></div>)}</div>
      : componentFacts.length ? <div><p className="mb-3 text-xs leading-5 text-slate-400">The package exposes component forecasts, not feature-level causal contributions. These values explain how the stored ensemble was formed.</p><div className="grid gap-2 sm:grid-cols-2">{componentFacts.map(([name, value]) => <div key={name} className="flex items-center justify-between rounded-lg border border-white/[0.07] bg-white/[0.025] px-3 py-2 text-xs"><span className="text-slate-300">{name}</span><strong className="text-cyan-200">{value.toFixed(2)}%</strong></div>)}</div></div>
      : <div className="rounded-xl border border-cyan-300/10 bg-cyan-300/[0.035] p-4"><p className="text-sm font-medium text-cyan-100">Forecast facts unavailable</p><p className="mt-1 text-xs text-slate-400">The selected response does not expose feature contributions or component forecasts.</p></div>}
  </Section>;
}

export function ForecastCalibration({ calibration }: { calibration?: ForecastCalibrationOutput | null }) {
  const coverage = (value: number | null) => value == null ? 'Unavailable' : `${(value * 100).toFixed(1)}%`;
  return <Section title="Forecast calibration" subtitle="Historical coverage from the stored comparison evaluation.">
    {calibration ? <div className="grid gap-3 sm:grid-cols-3">{[['80% interval coverage', coverage(calibration.coverage_80)], ['95% interval coverage', coverage(calibration.coverage_95)], ['Calibration status', calibration.status]].map(([label, value]) => <div key={label} className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4"><p className="text-xs text-slate-400">{label}</p><p className="mt-2 text-lg font-semibold text-slate-100">{value}</p></div>)}</div> : <div className="grid gap-3 sm:grid-cols-3">{['80% interval coverage', '95% interval coverage', 'Calibration status'].map((label) => <div key={label} className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4"><p className="text-xs text-slate-400">{label}</p><p className="mt-2 text-lg font-semibold text-slate-500">Not available</p></div>)}</div>}
    <p className="mt-3 text-[11px] text-slate-500">Intervals are based on development-period residuals and their displayed coverage is measured on the package comparison period.</p>
  </Section>;
}

export function ForecastVintageComparison() {
  const [runs, setRuns] = useState<ResearchRunResponse[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => { let active = true; getResearchRuns().then((items) => { if (active) setRuns(items.filter((item) => item.forecast)); }).catch(() => { if (active) setFailed(true); }); return () => { active = false; }; }, []);
  return <Section title="Forecast vintage comparison" subtitle="Only persisted research runs are listed; no sample dates are generated.">
    {failed ? <p className="text-sm text-slate-400">Stored forecast runs could not be loaded.</p> : runs.length ? <div className="space-y-2">{runs.map((run) => <article key={run.run_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3 text-xs"><span className="text-slate-200">Generated {new Date(run.created_at).toLocaleString()}</span><span className="text-slate-400">Data vintage: {run.data_vintage ?? 'not recorded'} · {run.forecast?.model ?? 'model not recorded'}</span><span className="font-semibold text-amber-200">{run.forecast?.forecasts?.[0]?.value ?? '—'} {run.forecast?.unit ?? ''}</span></article>)}</div> : <p className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4 text-sm text-slate-400">No stored forecast runs available.</p>}
  </Section>;
}

export function PendingIntelligence({ title, description, statusText = 'PLANNED' }: { title: string; description: string; statusText?: string }) {
  return <section className={panel}><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-base font-semibold text-slate-100">{title}</h2><p className="mt-1 text-xs leading-5 text-slate-400">{description}</p></div><span className={status}>{statusText}</span></div><div className="mt-4 rounded-xl border border-white/[0.06] bg-black/10 p-4 text-xs text-slate-500">No validated output is available. This module will display data after its backend integration is ready.</div></section>;
}
