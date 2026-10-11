import { CheckCircle2, TriangleAlert } from 'lucide-react';
import type { PolicyScorecardItem } from '@/lib/types';

interface PolicyScorecardProps {
	items: PolicyScorecardItem[];
	overallScore?: number;
}

export function PolicyScorecard({ items, overallScore }: PolicyScorecardProps) {
	const score = overallScore ?? Math.round(items.reduce((total, item) => total + item.score, 0) / Math.max(items.length, 1));
	return (
		<section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
			<div className="flex items-start justify-between"><div><h2 className="text-base font-semibold text-slate-950">Policy scorecard</h2><p className="mt-1 text-xs text-slate-500">Evidence-weighted demo assessment</p></div><span className="rounded-md bg-emerald-50 px-2 py-1 text-[10px] font-semibold text-emerald-700">{score} / 100</span></div>
			<div className="mt-5 space-y-4">{items.map((item) => <div key={item.dimension}><div className="flex items-center justify-between gap-3 text-xs"><span className="flex items-center gap-2 font-medium text-slate-700">{item.status === 'warning' ? <TriangleAlert size={14} className="text-amber-500" /> : <CheckCircle2 size={14} className="text-emerald-500" />}{item.dimension}</span><span className="font-semibold text-slate-900">{item.score}</span></div><div className="mt-2 h-1.5 rounded-full bg-slate-100"><div className={`h-full rounded-full ${item.status === 'warning' ? 'bg-amber-500' : 'bg-blue-600'}`} style={{ width: `${item.score}%` }} /></div></div>)}</div>
		</section>
	);
}
