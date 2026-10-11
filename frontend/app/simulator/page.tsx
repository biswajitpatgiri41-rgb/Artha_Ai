'use client';

import { useState } from 'react';
import { Activity, ArrowDownRight, ArrowUpRight, Gauge, Info, ShieldAlert } from 'lucide-react';
import { ConfidenceMeter, PolicyScorecard, SimulatorControls } from '@/components';
import { PageShell } from '@/components/layout';
import { defaultSimulatorInputs, baselineGrowth, calculateDemoSimulation, policyAlternatives } from '@/lib/simulator';
import { mockCpiInflation } from '@/lib/mock-data';
import type { PolicyAlternative, SimulatorInputs } from '@/lib/types';
import { ScenarioIntelligence } from '@/components/ScenarioPolicyIntelligence';
import { AskWhyButton } from '@/components/assistant/AskWhyButton';

const numericFields: Array<Exclude<keyof SimulatorInputs, 'policyAlternative'>> = ['oilPriceShock', 'inrShock', 'foodInflationShock', 'policyRateChangeBp', 'horizonMonths'];

function formatSigned(value: number, digits = 2) {
	return `${value > 0 ? '+' : ''}${value.toFixed(digits)}`;
}

function DistributionBars({ values, uncertainty }: { values: number[]; uncertainty: number }) {
	const min = Math.min(...values);
	const max = Math.max(...values);
	const range = Math.max(max - min, 0.01);

	return (
		<div className="mt-5 rounded-lg bg-slate-50 p-4">
			<div className="flex items-center justify-between"><div><h3 className="text-xs font-semibold text-slate-800">Uncertainty placeholder</h3><p className="mt-1 text-[10px] text-slate-500">Deterministic distribution around the demo scenario path</p></div><span className="text-[10px] font-medium text-amber-700">±{uncertainty.toFixed(2)} pp</span></div>
			<div className="mt-5 flex h-28 items-end justify-between gap-2" aria-label="Illustrative uncertainty distribution">
				{values.map((value, index) => <div key={`${value}-${index}`} className="flex flex-1 flex-col items-center gap-2"><div className="w-full rounded-t bg-blue-200" style={{ height: `${Math.max(18, ((value - min) / range) * 78 + 22)}px` }} title={`${value.toFixed(2)}%`} /><span className="text-[10px] text-slate-500">{value.toFixed(1)}%</span></div>)}
			</div>
			<p className="mt-3 text-[10px] leading-4 text-slate-400">Placeholder only. This is not a probability distribution or econometric confidence interval.</p>
		</div>
	);
}

export default function SimulatorPage() {
	const [inputs, setInputs] = useState<SimulatorInputs>(defaultSimulatorInputs);
	const result = calculateDemoSimulation(inputs);
	const selectedPolicy = policyAlternatives.find((alternative) => alternative.id === inputs.policyAlternative);
	const overallScore = Math.round(result.policyScorecard.reduce((sum, item) => sum + item.score, 0) / result.policyScorecard.length);
	const inflationDelta = result.scenarioInflation - result.baselineInflation;

	const updateInput = (field: Exclude<keyof SimulatorInputs, 'policyAlternative'>, value: number) => {
		setInputs((current) => ({ ...current, [field]: value }));
	};

	const updatePolicyAlternative = (alternative: PolicyAlternative) => {
		const selected = policyAlternatives.find((item) => item.id === alternative);
		setInputs((current) => ({ ...current, policyAlternative: alternative, policyRateChangeBp: selected?.basisPoints ?? current.policyRateChangeBp }));
	};

	return (
		<PageShell title="Scenario Simulator" description="Stress-test inflation and policy conditions under alternative macro shocks.">
			<div className="space-y-6">
				<ScenarioIntelligence />
				<div className="flex items-start gap-3 rounded-2xl border border-amber-300/15 bg-amber-400/[0.07] px-4 py-3 text-xs text-amber-100"><ShieldAlert size={17} className="mt-0.5 shrink-0 text-amber-300" /><div><strong>DEMO SIMULATION</strong><p className="mt-1 text-amber-200/70">Econometric backend not connected. Results are deterministic frontend demo output.</p></div></div>

				<div className="grid gap-5 xl:grid-cols-[360px_1fr]">
					<SimulatorControls inputs={inputs} onChange={updateInput} onPolicyAlternativeChange={updatePolicyAlternative} />

					<section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
						<div className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2"><Activity size={16} className="text-blue-600" /><h2 className="text-base font-semibold text-slate-950">Scenario output</h2><AskWhyButton chart={{ chartId: 'Scenario Results', selectedSeries: 'Demo baseline vs scenario CPI', selectedPoint: { date: `${inputs.horizonMonths}-month horizon`, value: result.scenarioInflation }, sourceMetadata: 'Frontend demo inputs; not an econometric result', mode: 'mock' }} /></div><p className="mt-1 text-xs text-slate-500">{selectedPolicy?.label} · {inputs.horizonMonths}-month horizon</p></div><span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">Frontend demo</span></div>
						<div className="mt-6 grid gap-3 sm:grid-cols-3">
							<div className="rounded-lg border border-slate-200 p-4"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">Inflation</p><div className="mt-3 flex items-end gap-2"><span className="text-2xl font-semibold text-slate-900">{result.scenarioInflation.toFixed(2)}%</span><span className={`mb-1 inline-flex items-center text-[10px] font-semibold ${inflationDelta > 0 ? 'text-red-600' : 'text-emerald-600'}`}>{inflationDelta > 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}{formatSigned(inflationDelta)} pp</span></div><p className="mt-2 text-[10px] text-slate-400">Baseline {result.baselineInflation.toFixed(1)}% · CPI {mockCpiInflation.date}</p></div>
							<div className="rounded-lg border border-slate-200 p-4"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">Potential growth impact</p><p className={`mt-3 text-2xl font-semibold ${result.potentialGrowthImpact < 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{formatSigned(result.potentialGrowthImpact)} pp</p><p className="mt-2 text-[10px] text-slate-400">Baseline demo growth {baselineGrowth.toFixed(1)}%</p></div>
							<div className="rounded-lg border border-slate-200 p-4"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">FX pressure</p><div className="mt-3 flex items-center gap-2"><Gauge size={18} className={result.fxPressure > 45 ? 'text-amber-600' : 'text-emerald-600'} /><span className="text-2xl font-semibold text-slate-900">{result.fxPressure}</span><span className="text-xs text-slate-400">/ 100</span></div><div className="mt-3 h-1.5 rounded-full bg-slate-100"><div className={`h-full rounded-full ${result.fxPressure > 45 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${result.fxPressure}%` }} /></div></div>
						</div>
						<DistributionBars values={result.distribution} uncertainty={result.uncertainty} />
						<div className="mt-5 flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50/60 p-3 text-xs leading-5 text-blue-900/75"><Info size={15} className="mt-0.5 shrink-0 text-blue-600" /><span>{result.interpretation}</span></div>
					</section>
				</div>

				<div className="grid gap-5 xl:grid-cols-[1fr_1.1fr]">
					<PolicyScorecard items={result.policyScorecard} overallScore={overallScore} />
					<section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><div className="flex items-start justify-between"><div><h2 className="text-base font-semibold text-slate-950">Input audit</h2><p className="mt-1 text-xs text-slate-500">Current parameters passed to the demo function</p></div><span className="text-[10px] uppercase tracking-[0.1em] text-slate-400">{numericFields.length} controls</span></div><div className="mt-5 grid gap-3 sm:grid-cols-2">{numericFields.map((field) => <div key={field} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs"><span className="text-slate-500">{field.replace(/([A-Z])/g, ' $1')}</span><strong className="text-slate-800">{inputs[field]}{field === 'horizonMonths' ? ' mo' : field === 'policyRateChangeBp' ? ' bp' : field === 'foodInflationShock' ? ' pp' : '%'}</strong></div>)}</div><div className="mt-5"><ConfidenceMeter value={Math.max(25, 100 - result.uncertainty * 18)} /></div></section>
				</div>
			</div>
		</PageShell>
	);
}
