import { X } from 'lucide-react';
import type { ArchitectureNode } from './architecture-model';

interface NodeInspectorProps { node: ArchitectureNode; onClose: () => void; }

const details: Record<string, { title: string; rows: Array<[string, string]> }> = {
  'Inflation Agent': { title: 'Agent', rows: [['Responsibility', 'Diagnose inflation channels and identify evidence.'], ['Inputs', 'CPI · Food CPI · Oil · INR'], ['Tools', 'get_series · compute_yoy · decompose_inflation'], ['Outputs', 'drivers · evidence · uncertainties'], ['Last execution', '1.23s']] },
  'RBI DBIE': { title: 'Source', rows: [['Type', 'Official macroeconomic database'], ['Series Requested', 'CPI · Repo Rate · INR/USD'], ['Status', 'MOCK']] },
  'Scenario Engine': { title: 'Scenario Engine', rows: [['Inputs', 'Oil +20% · INR -5% · Food +1.5pp'], ['Outputs', 'Inflation Impact · Growth Impact · FX Pressure'], ['Status', 'MOCK']] },
};

export function NodeInspector({ node, onClose }: NodeInspectorProps) {
  const info = details[node.data.label] ?? { title: node.data.category === 'source' ? 'Source' : node.data.category === 'agent' ? 'Agent' : 'Component', rows: [['Responsibility', node.data.description], ['Status', node.data.status.toUpperCase()], ['Last execution', 'MOCK DEMO']] };
  return <aside className="absolute right-4 top-4 z-20 w-[min(360px,calc(100%-2rem))] rounded-2xl border border-white/10 bg-[rgba(11,25,48,0.94)] p-5 text-slate-100 shadow-2xl backdrop-blur-2xl"><div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-300">{info.title}</p><h2 className="mt-1 text-lg font-semibold">{node.data.label}</h2></div><button type="button" onClick={onClose} aria-label="Close node inspector" className="rounded-md p-1 text-slate-500 hover:bg-white/10 hover:text-white"><X size={16} /></button></div><div className="mt-5 space-y-4">{info.rows.map(([label, value]) => <div key={label}><p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</p><p className="mt-1 text-xs leading-5 text-slate-300">{value}</p></div>)}</div><p className="mt-5 border-t border-white/[0.08] pt-3 text-[10px] uppercase tracking-[0.12em] text-amber-300">All execution details are demo data</p></aside>;
}