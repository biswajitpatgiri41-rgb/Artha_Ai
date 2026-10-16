'use client';

import { SlidersHorizontal } from 'lucide-react';
import type { PolicyAlternative, SimulatorInputs } from '@/lib/types';
import { policyAlternatives } from '@/lib/simulator';

type NumericSimulatorField = Exclude<keyof SimulatorInputs, 'policyAlternative'>;

interface SimulatorControlsProps {
  inputs: SimulatorInputs;
  onChange: (field: NumericSimulatorField, value: number) => void;
  onPolicyAlternativeChange: (alternative: PolicyAlternative) => void;
}

const shockFields: Array<{ field: 'oilPriceShock' | 'inrShock' | 'foodInflationShock'; label: string; unit: string; min: number; max: number; step: number }> = [
  { field: 'oilPriceShock', label: 'Oil price shock', unit: '%', min: -50, max: 100, step: 1 },
  { field: 'inrShock', label: 'INR shock', unit: '%', min: -20, max: 20, step: 1 },
  { field: 'foodInflationShock', label: 'Food inflation shock', unit: 'pp', min: -3, max: 5, step: 0.1 },
];

export function SimulatorControls({ inputs, onChange, onPolicyAlternativeChange }: SimulatorControlsProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2"><SlidersHorizontal size={16} className="text-blue-600" /><h2 className="text-base font-semibold text-slate-950">Shock configuration</h2></div>
          <p className="mt-1 text-xs text-slate-500">Adjust observed-data sensitivity inputs and inspect the API response.</p>
        </div>
        <span className="rounded-md bg-amber-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-amber-700">Sensitivity only</span>
      </div>

      <div className="mt-6 space-y-6">
        {shockFields.map((field) => (
          <label key={field.field} className="block">
            <div className="flex items-center justify-between gap-3 text-xs"><span className="font-medium text-slate-700">{field.label}</span><span className="flex items-center gap-1"><input type="number" value={inputs[field.field]} min={field.min} max={field.max} step={field.step} onChange={(event) => onChange(field.field, Number(event.target.value))} className="w-20 rounded-md border border-slate-200 px-2 py-1 text-right text-xs text-slate-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /><span className="w-5 text-slate-400">{field.unit}</span></span></div>
            <input aria-label={field.label} type="range" value={inputs[field.field]} min={field.min} max={field.max} step={field.step} onChange={(event) => onChange(field.field, Number(event.target.value))} className="mt-3 h-1.5 w-full cursor-pointer accent-blue-600" />
            <div className="mt-1 flex justify-between text-[10px] text-slate-400"><span>{field.min}{field.unit}</span><span>{field.max}{field.unit}</span></div>
          </label>
        ))}

        <label className="block"><div className="flex items-center justify-between gap-3 text-xs"><span className="font-medium text-slate-700">Policy rate change</span><span className="flex items-center gap-1"><input type="number" value={inputs.policyRateChangeBp} min={-100} max={100} step={25} onChange={(event) => onChange('policyRateChangeBp', Number(event.target.value))} className="w-20 rounded-md border border-slate-200 px-2 py-1 text-right text-xs text-slate-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /><span className="w-5 text-slate-400">bp</span></span></div><input aria-label="Policy rate change" type="range" value={inputs.policyRateChangeBp} min={-100} max={100} step={25} onChange={(event) => onChange('policyRateChangeBp', Number(event.target.value))} className="mt-3 h-1.5 w-full cursor-pointer accent-blue-600" /><div className="mt-1 flex justify-between text-[10px] text-slate-400"><span>-100 bp</span><span>+100 bp</span></div></label>

        <label className="block"><span className="text-xs font-medium text-slate-700">Horizon</span><select value={inputs.horizonMonths} onChange={(event) => onChange('horizonMonths', Number(event.target.value))} className="mt-2 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"><option value={3}>3 months</option><option value={6}>6 months</option><option value={9}>9 months</option><option value={12}>12 months</option></select></label>

        <div><p className="text-xs font-medium text-slate-700">Policy alternatives</p><div className="mt-2 grid grid-cols-3 gap-2">{policyAlternatives.map((alternative) => <button key={alternative.id} type="button" onClick={() => onPolicyAlternativeChange(alternative.id)} className={`rounded-lg border px-2 py-2 text-[11px] font-semibold transition ${inputs.policyAlternative === alternative.id ? 'border-blue-500 bg-blue-50 text-blue-800' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}>{alternative.label}</button>)}</div></div>
      </div>
    </section>
  );
}
