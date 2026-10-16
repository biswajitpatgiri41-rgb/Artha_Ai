'use client';

import { useEffect, useState } from 'react';
import { Activity, AlertTriangle } from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { SimulatorControls } from '@/components';
import { PageShell } from '@/components/layout';
import { defaultSimulatorInputs } from '@/lib/simulator';
import { getProjectSeriesObservations, simulateResearchScenario, type SimulationResponse } from '@/lib/research-api';
import type { SimulatorInputs } from '@/lib/types';

export default function SimulatorPage() {
  const [inputs, setInputs] = useState<SimulatorInputs>(defaultSimulatorInputs);
  const [baseline, setBaseline] = useState<number | null>(null);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => { getProjectSeriesObservations('cpi_yoy', 500).then((rows) => setBaseline(rows.at(-1)?.value ?? null)).catch(() => setBaseline(null)); }, []);
  const run = async () => {
    if (baseline === null) { setError('No observed CPI baseline is available.'); return; }
    setLoading(true); setError(null);
    try { setResult(await simulateResearchScenario({ base_inflation: baseline, oil_change_pct: inputs.oilPriceShock, inr_change_pct: inputs.inrShock, food_shock_pp: inputs.foodInflationShock, repo_change_bp: inputs.policyRateChangeBp, horizon_months: inputs.horizonMonths })); }
    catch (reason: unknown) { setError(reason instanceof Error ? reason.message : 'Scenario API unavailable.'); }
    finally { setLoading(false); }
  };
  const update = (field: Exclude<keyof SimulatorInputs, 'policyAlternative'>, value: number) => setInputs((current) => ({ ...current, [field]: value }));
  const chartOption = buildChartOption(result, baseline, inputs.horizonMonths);
  return <PageShell title="Scenario Simulator" description="Apply transparent sensitivity assumptions to the latest observed CPI baseline.">
    <div className="space-y-5">
      <div className="flex gap-3 rounded-xl border border-amber-300/20 bg-amber-400/[0.06] p-4 text-xs leading-5 text-amber-100"><AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-300"/><span><strong>Illustrative sensitivity only.</strong> The API applies fixed assumptions; this is not a trained causal model, probability forecast, or official policy analysis.</span></div>
      <div className="grid gap-5 xl:grid-cols-[360px_1fr]"><section className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><SimulatorControls inputs={inputs} onChange={update} onPolicyAlternativeChange={(policy) => setInputs((current) => ({ ...current, policyAlternative: policy }))}/><button onClick={run} disabled={loading || baseline === null} className="mt-5 w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold disabled:opacity-50">{loading ? 'Calculating…' : 'Calculate sensitivity'}</button><p className="mt-3 text-xs text-slate-400">Observed CPI baseline: {baseline === null ? 'Unavailable' : `${baseline.toFixed(2)}%`}</p></section>
        <section className="rounded-xl border border-cyan-300/10 bg-[radial-gradient(circle_at_80%_10%,rgba(34,211,238,0.09),transparent_35%),rgba(15,23,42,0.72)] p-5"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2"><Activity size={16} className="text-cyan-300"/><h2 className="text-base font-semibold">API scenario result</h2></div><span className="rounded-full border border-cyan-300/15 bg-cyan-300/[0.06] px-2 py-1 text-[9px] font-semibold uppercase tracking-wider text-cyan-200">{result ? 'Response loaded' : 'Awaiting response'}</span></div>{error && <p className="mt-4 text-sm text-rose-300">{error}</p>}<div className="mt-4 rounded-xl border border-white/[0.07] bg-slate-950/35 p-2"><div className="mb-1 flex items-center justify-between px-2 text-[10px]"><span className="font-semibold uppercase tracking-wider text-slate-400">Sensitivity path</span><span className="text-amber-200">{result ? 'API response' : 'Observed baseline'}</span></div><ReactECharts option={chartOption} style={{ height: 245, width: '100%' }} opts={{ renderer: 'svg' }} /></div>{!result && !error && <p className="mt-3 text-center text-xs text-slate-400">The observed CPI baseline is shown now. Run the API sensitivity calculation to plot the shocked path and channel effects.</p>}{result && <><div className="mt-5 grid gap-3 sm:grid-cols-3"><Metric label="Baseline CPI" value={`${result.baseline_inflation.toFixed(2)}%`}/><Metric label="Sensitivity output" value={`${result.scenario_inflation.toFixed(2)}%`}/><Metric label="Change" value={`${result.change_pp > 0 ? '+' : ''}${result.change_pp.toFixed(2)} pp`}/></div><div className="mt-5 grid gap-3 sm:grid-cols-2">{Object.entries(result.effects_pp).map(([name, value]) => <div key={name} className="flex justify-between rounded-lg bg-white/[0.04] px-3 py-2 text-xs"><span className="capitalize text-slate-400">{name} effect</span><strong>{value > 0 ? '+' : ''}{value.toFixed(3)} pp</strong></div>)}</div>{result.warnings.map((warning) => <p key={warning} className="mt-3 text-xs leading-5 text-amber-100/70">{warning}</p>)}</>}</section></div>
    </div>
  </PageShell>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-white/[0.08] p-4"><p className="text-[10px] uppercase tracking-wider text-slate-400">{label}</p><p className="mt-2 text-2xl font-semibold text-slate-50">{value}</p></div>; }

function buildChartOption(result: SimulationResponse | null, baseline: number | null, horizon: number) {
  const base = result?.baseline_inflation ?? baseline;
  const labels = ['Now', '+1M', '+3M', `+${horizon}M`];
  const baselineLine = base == null ? [] : labels.map(() => base);
  const shockedLine = result
    ? labels.map((_, index) => result.baseline_inflation + (result.change_pp * [0, 1 / 6, 3 / 6, 1][index]))
    : [];
  const values = [...baselineLine, ...shockedLine];
  const spread = Math.max((Math.max(...values, base ?? 0) - Math.min(...values, base ?? 0)) * 0.35, 0.35);
  return {
    animation: false,
    grid: { left: 48, right: 18, top: 24, bottom: 28 },
    legend: { show: Boolean(result), textStyle: { color: '#94a3b8', fontSize: 10 }, top: 0 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(7,20,38,0.96)', borderColor: 'rgba(255,255,255,0.12)', textStyle: { color: '#f8fafc', fontSize: 10 }, valueFormatter: (value: number) => `${value.toFixed(2)}%` },
    xAxis: { type: 'category', data: labels, boundaryGap: false, axisLine: { lineStyle: { color: 'rgba(148,163,184,0.2)' } }, axisTick: { show: false }, axisLabel: { color: '#64748b', fontSize: 10 } },
    yAxis: { type: 'value', min: base == null ? 0 : Math.max(0, base - spread), max: base == null ? 10 : base + spread, axisLabel: { color: '#64748b', fontSize: 9, formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.1)' } } },
    series: [
      { name: 'Observed baseline', type: 'line', data: baselineLine, showSymbol: false, smooth: false, lineStyle: { color: '#38bdf8', width: 2, type: 'dashed' }, areaStyle: { color: 'rgba(56,189,248,0.06)' } },
      ...(result ? [{ name: 'Sensitivity output', type: 'line', data: shockedLine, showSymbol: true, symbolSize: 7, smooth: false, lineStyle: { color: '#fb7185', width: 3 }, itemStyle: { color: '#fb7185' } }] : []),
    ],
    graphic: !result ? [{ type: 'text', left: 'center', top: '45%', style: { text: base == null ? 'Baseline unavailable' : 'Run sensitivity to compare paths', fill: 'rgba(226,232,240,0.72)', fontSize: 12, fontWeight: 600 } }] : [],
  };
}
