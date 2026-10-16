'use client';

import { ArrowRight, BarChart3, Flame, Globe2, Leaf, Loader2, Play, SlidersHorizontal } from 'lucide-react';
import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { defaultSimulatorInputs } from '@/lib/simulator';
import { simulateResearchScenario, type SimulationResponse } from '@/lib/research-api';
import type { SimulatorInputs } from '@/lib/types';
import { Skeleton } from './skeletons/Skeleton';

interface ScenarioPathData {
	dates: string[];
	baseline: number[];
	shocked: number[];
	lower80?: number[];
	upper80?: number[];
}

function buildScenarioPath(result: SimulationResponse): ScenarioPathData {
	const dates = ['Now', '+1M', '+3M', `+${result.horizon_months}M`];
	const progress = [0, 1 / 6, 3 / 6, 1];
	const difference = result.scenario_inflation - result.baseline_inflation;
	return {
		dates,
		baseline: dates.map(() => result.baseline_inflation),
		shocked: progress.map((step) => result.baseline_inflation + difference * step),
	};
}

function ScenarioPathChart({ data }: { data: ScenarioPathData }) {
	const allValues = [...data.baseline, ...data.shocked, ...(data.lower80 || []), ...(data.upper80 || [])];
	const spread = Math.max(Math.max(...allValues) - Math.min(...allValues), 0.5);
	const padding = spread * 0.18;
	const hasConfidenceBands = data.lower80 && data.upper80 && data.lower80.length === data.dates.length && data.upper80.length === data.dates.length;

	const series = [];
	if (hasConfidenceBands) {
		series.push(
			{
				name: '80% CI',
				type: 'line',
				data: data.upper80!,
				showSymbol: false,
				lineStyle: { width: 0 },
				itemStyle: { color: 'rgba(251,113,133,0)' },
				areaStyle: { color: 'rgba(251,113,133,0.08)' },
				stack: 'confidence',
			},
			{
				name: '80% CI',
				type: 'line',
				data: data.lower80!,
				showSymbol: false,
				lineStyle: { width: 0 },
				itemStyle: { color: 'rgba(251,113,133,0)' },
				areaStyle: { color: 'rgba(7,20,38,0.96)' },
				stack: 'confidence',
			}
		);
	}

	series.push(
		{ name: 'BASELINE', type: 'line', data: data.baseline, showSymbol: false, lineStyle: { width: 2, type: 'dashed', color: '#38bdf8' }, itemStyle: { color: '#38bdf8' } },
		{ name: 'SHOCKED', type: 'line', data: data.shocked, showSymbol: true, symbolSize: 5, lineStyle: { width: 2.5, color: '#fb7185' }, itemStyle: { color: '#fb7185' } }
	);

	const option = {
		animation: false,
		grid: { left: 48, right: 12, top: 12, bottom: 24 },
		tooltip: {
			trigger: 'axis',
			backgroundColor: 'rgba(7,20,38,0.96)',
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: '#f8fafc', fontSize: 10 },
			valueFormatter: (value: number) => `${value.toFixed(2)}%`,
		},
		xAxis: {
			type: 'category', data: data.dates, boundaryGap: false,
			axisLine: { lineStyle: { color: 'rgba(148,163,184,0.2)' } },
			axisTick: { show: false }, axisLabel: { color: '#64748b', fontSize: 9 },
		},
		yAxis: {
			type: 'value', name: 'CPI Inflation (%)',
			nameTextStyle: { color: '#64748b', fontSize: 9 },
			min: Math.min(...allValues) - padding, max: Math.max(...allValues) + padding,
			splitNumber: 3,
			axisLabel: { color: '#64748b', fontSize: 9, formatter: '{value}%' },
			splitLine: { lineStyle: { color: 'rgba(148,163,184,0.1)' } },
		},
		series,
		graphic: [
			{
				type: 'text',
				left: 'center',
				bottom: 8,
				style: {
					text: 'Illustrative sensitivity — not a forecast',
					fontSize: 9,
					fill: 'rgba(245,158,11,0.7)',
					fontWeight: 500,
				},
			},
		],
	};
	return <ReactECharts option={option} style={{ height: '100%', width: '100%' }} opts={{ renderer: 'svg' }} />;
}

const controls: Array<{ field: 'oilPriceShock' | 'inrShock' | 'foodInflationShock'; label: string; unit: string; min: number; max: number; step: number }> = [
	{ field: 'oilPriceShock', label: 'Oil Price Shock', unit: '%', min: -50, max: 100, step: 1 },
	{ field: 'inrShock', label: 'INR Shock', unit: '%', min: -20, max: 20, step: 1 },
	{ field: 'foodInflationShock', label: 'Food Inflation', unit: 'pp', min: -3, max: 5, step: 0.1 },
];

export function ScenarioLab({ baselineInflation, baselineDate }: { baselineInflation?: number; baselineDate?: string }) {
	const [inputs, setInputs] = useState<SimulatorInputs>({ ...defaultSimulatorInputs, oilPriceShock: 20, inrShock: -5, foodInflationShock: 1.5 });
	const [result, setResult] = useState<SimulationResponse | null>(null);
	const [hasRun, setHasRun] = useState(false);
	const [isRunning, setIsRunning] = useState(false);
	const [runError, setRunError] = useState<string | null>(null);
	const update = (field: keyof SimulatorInputs, value: number) => setInputs((current) => ({ ...current, [field]: value }));

	const runScenario = async () => {
		setIsRunning(true);
		setHasRun(false);
		setRunError(null);
		try {
			const response = await simulateResearchScenario({
				base_inflation: baselineInflation ?? 0,
				oil_change_pct: inputs.oilPriceShock,
				inr_change_pct: inputs.inrShock,
				food_shock_pp: inputs.foodInflationShock,
				repo_change_bp: inputs.policyRateChangeBp,
				horizon_months: inputs.horizonMonths,
			});
			setResult(response);
			setHasRun(true);
		} catch (error) {
			setRunError(error instanceof Error ? error.message : 'The scenario could not be calculated.');
		} finally {
			setIsRunning(false);
		}
	};

	const inflationDelta = result ? result.scenario_inflation - result.baseline_inflation : 0;
	const scenarioPath = result ? buildScenarioPath(result) : null;
	const shockLevels = [
		{ label: 'Oil', value: inputs.oilPriceShock, unit: '%', color: 'bg-amber-400', max: 100 },
		{ label: 'INR', value: inputs.inrShock, unit: '%', color: 'bg-cyan-400', max: 20 },
		{ label: 'Food', value: inputs.foodInflationShock, unit: 'pp', color: 'bg-rose-400', max: 5 },
	];

	return (
		<section className="relative h-full overflow-hidden rounded-[18px] border border-amber-300/15 bg-[rgba(15,23,42,0.66)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.25),0_0_30px_rgba(245,158,11,0.045)] backdrop-blur-2xl">
			<span className="pointer-events-none absolute -bottom-20 -right-16 h-48 w-48 rounded-full bg-cyan-400/[0.08] blur-3xl" />
			<div className="relative flex items-start justify-between gap-4"><div><div className="flex items-center gap-2"><SlidersHorizontal size={16} className="text-amber-300" /><h2 className="text-base font-semibold text-slate-50">Scenario Lab</h2></div><p className="mt-1 text-xs text-slate-400">Backend sensitivity calculation using the latest validated CPI baseline ({baselineInflation?.toFixed(2) ?? 'Unavailable'}%{baselineDate ? ` · ${baselineDate.slice(0, 7)}` : ''}). Not an estimated or causal model.</p></div><span className="rounded-full border border-amber-300/15 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold text-amber-300">Illustrative</span></div>
			<div className="relative mt-5 grid gap-x-5 gap-y-4 md:grid-cols-3">{controls.map((control) => <label key={control.field} className="block"><div className="flex items-center justify-between gap-2 text-[11px]"><span className="font-medium text-slate-300">{control.label}</span><strong className="tabular-nums text-cyan-300">{inputs[control.field] > 0 ? '+' : ''}{inputs[control.field]} {control.unit}</strong></div><input aria-label={control.label} type="range" min={control.min} max={control.max} step={control.step} value={inputs[control.field]} onChange={(event) => update(control.field, Number(event.target.value))} className="mt-3 h-1.5 w-full cursor-pointer accent-cyan-400" /></label>)}</div>
			<div className="relative mt-5 flex flex-wrap items-center gap-3"><button type="button" disabled={isRunning || baselineInflation == null} onClick={runScenario} className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-2.5 text-xs font-semibold text-white shadow-[0_8px_22px_rgba(59,130,246,0.24)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_10px_26px_rgba(34,211,238,0.2)] disabled:cursor-wait disabled:opacity-70">{isRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />}{isRunning ? 'Running…' : 'Run Scenario'}</button><span role="status" className="text-[10px] text-slate-500">{isRunning ? 'Requesting backend sensitivity…' : runError ? 'Backend unavailable' : hasRun ? 'Backend responded · illustrative only' : 'Ready · illustrative backend'}</span></div>
			<div className="relative mt-5 border-t border-white/[0.07] pt-4"><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Scenario impact</p><div className="mt-3 grid gap-2 sm:grid-cols-3"><div className="rounded-lg border border-rose-400/10 bg-rose-400/[0.06] px-3 py-2"><p className="text-[10px] text-slate-500">Inflation change</p><p className="mt-1 text-xs font-semibold text-rose-300">{hasRun ? `${inflationDelta > 0 ? '+' : ''}${inflationDelta.toFixed(2)} pp` : '—'}</p></div><div className="rounded-lg border border-amber-400/10 bg-amber-400/[0.06] px-3 py-2"><p className="text-[10px] text-slate-500">Growth impact</p><p className="mt-1 text-xs font-semibold text-amber-300">Not estimated</p></div><div className="rounded-lg border border-cyan-400/10 bg-cyan-400/[0.06] px-3 py-2"><p className="text-[10px] text-slate-500">FX pressure</p><p className="mt-1 text-xs font-semibold text-cyan-300">Not estimated</p></div></div></div>

			<div className="relative mt-5 border-t border-white/[0.07] pt-4">
				<div className="mb-3 flex flex-wrap items-end justify-between gap-2"><div><h3 className="text-xs font-semibold text-slate-200">Baseline vs Shocked CPI</h3><p className="mt-1 text-[10px] text-slate-500">Straight-line illustration between backend-calculated endpoints; not a forecast.</p></div><span className="rounded-full border border-amber-300/10 bg-amber-300/[0.06] px-2 py-1 text-[9px] font-medium text-amber-200">Illustrative backend result</span></div>
				{runError && <p role="alert" className="mb-3 rounded-lg border border-rose-300/15 bg-rose-400/[0.06] px-3 py-2 text-[10px] text-rose-200">{runError}</p>}
				<div className="grid gap-3 lg:grid-cols-[minmax(0,1.5fr)_minmax(150px,0.65fr)]">
					<div className="min-w-0 rounded-xl border border-white/[0.07] bg-slate-950/20 p-2">{isRunning ? <div className="space-y-3 p-3" aria-label="Loading scenario chart"><Skeleton variant="rectangular" width="100%" height={132} /><div className="flex gap-3"><Skeleton width="35%" height={10} /><Skeleton width="28%" height={10} /></div></div> : !hasRun || !scenarioPath ? <div className="flex min-h-[164px] flex-col items-center justify-center gap-2 px-4 text-center"><BarChart3 size={23} className="text-cyan-300/70" /><p className="text-[11px] font-medium text-slate-300">Run a scenario to compare baseline and shocked endpoints</p><p className="text-[10px] text-slate-500">The API returns an illustrative sensitivity, not a forecast path.</p></div> : <div className="h-[164px] w-full"><ScenarioPathChart data={scenarioPath} /></div>}</div>
					<div className="flex flex-col justify-center gap-2 rounded-xl border border-white/[0.07] bg-white/[0.02] p-3"><p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">Scenario delta</p><div className="flex items-center justify-between gap-2 text-[11px]"><span className="text-slate-400">Mock baseline CPI</span><strong className="tabular-nums text-slate-200">{hasRun && result ? `${result.baseline_inflation.toFixed(2)}%` : '—'}</strong></div><div className="flex items-center justify-between gap-2 text-[11px]"><span className="text-slate-400">Scenario endpoint</span><strong className="tabular-nums text-slate-200">{hasRun && result ? `${result.scenario_inflation.toFixed(2)}%` : '—'}</strong></div><div className="mt-1 flex items-center justify-between gap-2 border-t border-white/[0.07] pt-2 text-[11px]"><span className="text-slate-400">Difference</span><strong className={`tabular-nums ${inflationDelta > 0 ? 'text-rose-300' : inflationDelta < 0 ? 'text-emerald-300' : 'text-slate-300'}`}>{hasRun ? `${inflationDelta > 0 ? '+' : ''}${inflationDelta.toFixed(2)} pp` : '—'}</strong></div></div>
				</div>
				<div className="mt-4"><h3 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Illustrative sensitivity by channel</h3><div className="mt-2 grid gap-2 sm:grid-cols-3">{[
					{ title: 'OIL SHOCK', label: 'Oil Prices', effect: result?.effects_pp.oil, icon: Flame, color: 'text-amber-300', border: 'border-amber-300/10' },
					{ title: 'FX SHOCK', label: 'INR movement', effect: result?.effects_pp.inr, icon: Globe2, color: 'text-cyan-300', border: 'border-cyan-300/10' },
					{ title: 'FOOD SHOCK', label: 'Food prices', effect: result?.effects_pp.food, icon: Leaf, color: 'text-rose-300', border: 'border-rose-300/10' },
				].map((channel) => { const Icon = channel.icon; return <div key={channel.title} className={`rounded-lg border ${channel.border} bg-white/[0.02] px-3 py-2`}><div className="flex items-center gap-2"><Icon size={13} className={channel.color} /><span className={`text-[9px] font-semibold tracking-[0.1em] ${channel.color}`}>{channel.title}</span></div><p className="mt-1 text-[10px] font-medium text-slate-300">{channel.label}</p><p className="mt-1 flex items-center gap-1 text-[9px] text-slate-500">{channel.effect === undefined ? 'Run the backend sensitivity to view effect' : `${channel.effect > 0 ? '+' : ''}${channel.effect.toFixed(2)} pp illustrative effect`} <ArrowRight size={10} /> CPI</p></div>; })}</div></div>
				<div className="mt-4 grid gap-2 sm:grid-cols-3">{shockLevels.map((shock) => { const width = Math.min(100, Math.abs(shock.value) / shock.max * 100); return <div key={shock.label} className="flex items-center gap-2"><span className="w-9 text-[9px] font-medium text-slate-500">{shock.label}</span><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.07]"><div className={`h-full rounded-full ${shock.color}`} style={{ width: `${width}%` }} /></div><span className="w-12 text-right text-[9px] tabular-nums text-slate-400">{shock.value > 0 ? '+' : ''}{shock.value}{shock.unit}</span></div>; })}</div>
			</div>
		</section>
	);
}
