'use client';

import { useState } from 'react';
import { ArrowRight, SlidersHorizontal } from 'lucide-react';
import type { ScenarioResult } from '@/lib/types';

interface ScenarioControlsProps {
	scenarios: ScenarioResult[];
}

export function ScenarioControls({ scenarios }: ScenarioControlsProps) {
	const [selectedId, setSelectedId] = useState(scenarios[0]?.id ?? '');
	const selected = scenarios.find((scenario) => scenario.id === selectedId) ?? scenarios[0];

	return (
		<section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
			<div className="flex items-start justify-between gap-4">
				<div><div className="flex items-center gap-2"><SlidersHorizontal size={16} className="text-blue-600" /><h2 className="text-base font-semibold text-slate-950">Scenario analysis</h2></div><p className="mt-1 text-xs text-slate-500">Compare mock policy paths before connecting a simulator.</p></div>
				<span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">Demo</span>
			</div>
			<div className="mt-5 grid gap-2 sm:grid-cols-3">
				{scenarios.map((scenario) => <button key={scenario.id} type="button" onClick={() => setSelectedId(scenario.id)} className={`rounded-lg border px-3 py-2 text-left text-xs transition ${selected?.id === scenario.id ? 'border-blue-500 bg-blue-50 text-blue-800' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'}`}><span className="block font-semibold">{scenario.name}</span><span className="mt-1 block text-[10px] opacity-70">Rate {scenario.repoRateChange.value > 0 ? '+' : ''}{scenario.repoRateChange.value.toFixed(2)} pp</span></button>)}
			</div>
			{selected && <div className="mt-5 grid gap-4 rounded-lg bg-slate-50 p-4 sm:grid-cols-3"><div><p className="text-[10px] uppercase tracking-[0.12em] text-slate-400">Inflation</p><p className="mt-1 text-lg font-semibold text-slate-900">{selected.inflation.value.toFixed(1)}%</p></div><div><p className="text-[10px] uppercase tracking-[0.12em] text-slate-400">GDP growth</p><p className="mt-1 text-lg font-semibold text-slate-900">{selected.gdpGrowth.value.toFixed(1)}%</p></div><div><p className="text-[10px] uppercase tracking-[0.12em] text-slate-400">Confidence</p><p className="mt-1 text-lg font-semibold text-slate-900">{Math.round(selected.confidence * 100)}%</p></div><p className="text-xs leading-5 text-slate-500 sm:col-span-3">{selected.description} <span className="inline-flex items-center gap-1 font-medium text-blue-700">View scenario detail <ArrowRight size={12} /></span></p></div>}
		</section>
	);
}
