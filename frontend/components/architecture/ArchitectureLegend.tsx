'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const categories = [
  ['Data Sources', '#22D3EE'], ['Data Engineering', '#3B82F6'], ['Forecast Models', '#F59E0B'], ['Explainability', '#22D3EE'], ['Regime Detection', '#A78BFA'], ['Evaluation', '#A3E635'], ['Scenario', '#F472B6'], ['Policy / Agents', '#A78BFA'], ['Evidence / RAG', '#2DD4BF'], ['Critic / Validation', '#FB7185'], ['Output', '#34D399'],
] as const;

export function ArchitectureLegend() {
  const [open, setOpen] = useState(true);
  return <div className="border-b border-white/[0.06] px-4 py-2 sm:px-5"><button type="button" onClick={() => setOpen((value) => !value)} className="flex items-center gap-2 text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-500"><span>Architecture legend</span>{open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}</button>{open && <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[9px] text-slate-400"><div className="flex flex-wrap gap-x-3 gap-y-1.5">{categories.map(([label, color]) => <span key={label} className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />{label}</span>)}</div><span className="hidden text-slate-700 sm:inline">|</span><span className="inline-flex items-center gap-1 text-slate-400"><span className="text-[13px] leading-none">──→</span> Data flow</span><span className="inline-flex items-center gap-1 text-cyan-300"><span className="text-[13px] leading-none">●────→</span> Active transfer</span><span className="inline-flex items-center gap-1 text-emerald-300"><span>✓</span> Completed</span><span className="inline-flex items-center gap-1 text-slate-500"><span>○</span> Not connected</span></div>}</div>;
}
