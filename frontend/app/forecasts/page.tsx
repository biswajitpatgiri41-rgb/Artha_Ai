'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BarChart3 } from 'lucide-react';
import { PageShell } from '@/components/layout';
import { StatusState } from '@/components/ui';
import { getFinalPackageForecast, getFinalModelExplanation, getFinalModelRegistry, type ForecastResponse, type PackagedModelRegistry } from '@/lib/research-api';
import { ForecastCalibration, ForecastExplainability, ForecastVintageComparison, ModelEnsembleComparison, type ForecastExplanationOutput } from '@/components/ForecastIntelligence';
import { AskWhyButton } from '@/components/assistant/AskWhyButton';

const modelOptions = [
  { id: 'seasonal_naive', label: 'Seasonal Naive' },
  { id: 'arima', label: 'ARIMA (1,0,0)' },
  { id: 'ets', label: 'ETS' },
  { id: 'xgboost', label: 'XGBoost' },
  { id: 'sarima', label: 'SARIMA' },
  { id: 'sarimax', label: 'SARIMAX' },
  { id: 'var', label: 'VAR' },
  { id: 'ensemble', label: 'Development weighted ensemble' },
];
const selectClass = 'rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-300/40';

export default function ForecastsPage() {
  const [horizon, setHorizon] = useState(6);
  const [model, setModel] = useState('ensemble');
  const [variant, setVariant] = useState('mospi_2024_base');
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [explanation, setExplanation] = useState<ForecastExplanationOutput | null>(null);
  const [registry, setRegistry] = useState<PackagedModelRegistry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      Promise.all([getFinalPackageForecast(horizon, model, variant), getFinalModelRegistry(), getFinalModelExplanation(horizon, model, variant)])
        .then(([forecastResult, registryResult, explanationResult]) => {
          if (!active) return;
          setForecast(forecastResult);
          setRegistry(registryResult);
          setExplanation(explanationResult);
        })
        .catch((reason: unknown) => {
          if (active) setError(reason instanceof Error ? reason.message : 'Could not load the packaged forecast.');
        })
        .finally(() => { if (active) setLoading(false); });
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [horizon, model, variant]);

  const comparison = useMemo(() => registry?.metrics.filter((item) =>
    item.horizon_months === horizon && item.variant === variant,
  ) ?? [], [registry, horizon, variant]);
  const selectedValue = forecast?.forecasts.find((item) => item.step === horizon)?.value;
  const interval80 = forecast?.intervals?.['80'];

  return <PageShell title="Forecasts" description="Run the packaged India CPI research models and inspect their rolling holdout performance.">
    <div className="space-y-5">
      <div className="flex items-start gap-3 rounded-2xl border border-amber-300/15 bg-amber-400/[0.07] px-4 py-3 text-xs leading-5 text-amber-100">
        <AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-300" />
        <span><strong>EXPERIMENTAL RESEARCH MODEL</strong><span className="ml-2 text-amber-100/75">Forecasts are stored model-package snapshots, not live predictions. The comparison period was used for model selection and is not an untouched production holdout.</span></span>
      </div>

      <section className="rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.22)] backdrop-blur-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-300">Packaged CPI models</p><h2 className="mt-1 text-base font-semibold text-slate-50">Forecast controls</h2></div>
          <div className="flex flex-wrap gap-2">
            <label className="sr-only" htmlFor="forecast-model">Forecast model</label>
            <select id="forecast-model" className={selectClass} value={model} onChange={(event) => setModel(event.target.value)}>{modelOptions.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select>
            <label className="sr-only" htmlFor="forecast-variant">Feature variant</label>
            <select id="forecast-variant" className={selectClass} value={variant} onChange={(event) => setVariant(event.target.value)}>{(registry?.variants ?? ['mospi_2024_base', 'mospi_2024_base_extended', 'oecd_long_history_sensitivity']).map((item) => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select>
            <label className="sr-only" htmlFor="forecast-horizon">Forecast horizon</label>
            <select id="forecast-horizon" className={selectClass} value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}>{[1, 3, 6, 12].map((months) => <option key={months} value={months}>{months} month{months > 1 ? 's' : ''}</option>)}</select>
          </div>
        </div>

        {loading ? <div className="mt-5"><StatusState kind="loading" title="Loading packaged model" message="Reading the selected model and its evaluation record." /></div>
          : error ? <div className="mt-5"><StatusState kind="error" title="Forecast unavailable" message={error} /></div>
          : forecast && <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04] p-4"><div className="flex items-center justify-between"><p className="text-[10px] uppercase tracking-wider text-slate-400">Forecast CPI YoY</p><AskWhyButton chart={{ chartId: 'Forecast Chart', selectedSeries: forecast.series_id, visibleDateRange: { start: forecast.origin, end: forecast.target_month }, selectedPoint: forecast.target_month ? { date: forecast.target_month, value: selectedValue } : undefined, modelVersion: forecast.package_created_at ? `${forecast.variant}@${forecast.package_created_at}` : model, sourceMetadata: forecast.source, mode: 'live' }} /></div><p className="mt-2 text-3xl font-semibold text-cyan-100">{selectedValue?.toFixed(2) ?? '—'}%</p><p className="mt-1 text-xs text-slate-400">{forecast.target_month ?? `Horizon ${horizon} months`}</p><p className="mt-2 text-[11px] text-slate-500">80% historical interval: {interval80?.lower?.toFixed(2) ?? '—'}–{interval80?.upper?.toFixed(2) ?? '—'}%</p></div>
            <div className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4"><p className="text-[10px] uppercase tracking-wider text-slate-400">Model</p><p className="mt-2 text-lg font-semibold text-slate-100">{modelOptions.find((item) => item.id === model)?.label}</p><p className="mt-1 text-xs text-slate-400">Feature variant: {forecast.variant ?? variant}</p></div>
            <div className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4"><p className="text-[10px] uppercase tracking-wider text-slate-400">Data vintage</p><p className="mt-2 text-lg font-semibold text-slate-100">{forecast.origin}</p><p className="mt-1 text-xs text-slate-400">Bundled observed panel</p></div>
            <div className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-4"><p className="text-[10px] uppercase tracking-wider text-slate-400">Training target</p><p className="mt-2 text-lg font-semibold text-slate-100">{forecast.dataset_start} → {forecast.dataset_end}</p><p className="mt-1 text-xs text-slate-400">{forecast.source_observations} CPI observations</p></div>
          </div>}

        {forecast && !loading && <div className="mt-4 flex items-center gap-2 text-xs text-slate-400"><BarChart3 size={14} className="text-cyan-300" /> Numerical forecast from the deterministic model adapter · no LLM forecast generation</div>}
        {forecast?.warnings.map((warning) => <p key={warning} className="mt-2 text-xs leading-5 text-amber-100/70">{warning}</p>)}
      </section>

      <section className="rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.22)] backdrop-blur-2xl">
        <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-lime-300">Model evaluation</p><h2 className="mt-1 text-base font-semibold text-slate-50">Rolling holdout comparison · {horizon} month horizon</h2></div><span className="text-xs text-slate-500">{registry?.test_period ? `${registry.test_period.start} — ${registry.test_period.end} · 24 forecast origins` : 'Metrics are loaded from the packaged evaluation results'}</span></div>
        {comparison.length ? <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[600px] text-left text-xs"><thead className="text-[10px] uppercase tracking-wider text-slate-500"><tr><th className="px-3 py-2">Model</th><th className="px-3 py-2">Variant</th><th className="px-3 py-2">MAE (pp)</th><th className="px-3 py-2">RMSE (pp)</th><th className="px-3 py-2">Bias (pp)</th><th className="px-3 py-2">Origins</th></tr></thead><tbody>{comparison.map((item) => <tr key={`${item.model}-${item.variant}-${item.horizon_months}`} className="border-t border-white/[0.06] text-slate-300"><td className="px-3 py-3 font-medium text-slate-100">{item.model_label}</td><td className="px-3 py-3">{item.variant}</td><td className="px-3 py-3">{item.mae_pp.toFixed(3)}</td><td className="px-3 py-3">{item.rmse_pp.toFixed(3)}</td><td className="px-3 py-3">{item.bias_pp.toFixed(3)}</td><td className="px-3 py-3">{item.test_origins}</td></tr>)}</tbody></table></div> : !loading && <p className="mt-4 text-sm text-slate-400">No evaluation rows are available for this feature variant and horizon.</p>}
        {registry?.warnings.slice(0, 3).map((warning) => <p key={warning} className="mt-2 text-xs leading-5 text-slate-500">{warning}</p>)}
      </section>
      <section aria-labelledby="forecast-intelligence-heading" className="space-y-4">
        <div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-amber-300">Advanced forecast tools</p><h2 id="forecast-intelligence-heading" className="mt-1 text-lg font-semibold text-slate-50">Forecast Intelligence</h2><p className="mt-1 text-xs text-slate-400">Extensions use existing model records where available and explicitly identify pending artifacts.</p></div>
        <ModelEnsembleComparison registry={registry} horizon={horizon} variant={variant} />
        <div className="grid gap-4 xl:grid-cols-2"><ForecastExplainability explanation={explanation} /><ForecastCalibration calibration={forecast?.calibration ?? null} /></div>
        <ForecastVintageComparison />
      </section>
    </div>
  </PageShell>;
}
