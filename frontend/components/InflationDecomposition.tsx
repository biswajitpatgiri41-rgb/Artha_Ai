'use client';

import ReactECharts from 'echarts-for-react';
import type { InflationDecompositionItem } from '@/lib/types';
import { StatusState } from './ui';
import { AskWhyButton } from './assistant/AskWhyButton';

interface InflationDecompositionProps {
	items: InflationDecompositionItem[];
	isLoading?: boolean;
}

export function InflationDecomposition({ items, isLoading = false }: InflationDecompositionProps) {
	const colors = ['#10B981', '#F59E0B', '#3B82F6'];
	const hasData = items.length > 0;
	const latestDate = items[0]?.contribution.date;
	const sources = [...new Set(items.map((item) => item.contribution.source))];
	const option = {
		animation: false,
		tooltip: { trigger: 'item', backgroundColor: 'rgba(7, 20, 38, 0.94)', borderColor: 'rgba(255,255,255,0.12)', textStyle: { color: '#f8fafc', fontSize: 11 }, formatter: '{b}<br/><strong>{c} pp</strong> ({d}%)' },
		legend: { show: false },
		graphic: [{ type: 'text', left: 'center', top: '45%', style: { text: hasData ? `${items.reduce((sum, item) => sum + item.contribution.value, 0).toFixed(1)} pp` : 'Unavailable', fill: '#f8fafc', fontSize: 22, fontWeight: 700, textAlign: 'center' } }, { type: 'text', left: 'center', top: '58%', style: { text: 'Validated inputs only', fill: '#94a3b8', fontSize: 10, textAlign: 'center' } }],
		series: [{ name: 'Contribution', type: 'pie', radius: ['57%', '78%'], center: ['50%', '49%'], avoidLabelOverlap: true, itemStyle: { borderColor: '#0f172a', borderWidth: 4 }, label: { show: false }, emphasis: { label: { show: false } }, data: items.map((item, index) => ({ name: item.category, value: item.contribution.value, itemStyle: { color: colors[index % colors.length] } })) }],
	};

	return (
		<section className="rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.25)] backdrop-blur-2xl">
			<div className="flex items-start justify-between">
				<div>
					<div className="flex items-center gap-2">
						<span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.45)]" />
						<h2 className="text-base font-semibold text-slate-50">Inflation Decomposition</h2>
					</div>
					<p className="mt-1 text-xs text-slate-400">Contribution to headline CPI</p>
				</div>
				<div className="flex items-center gap-2"><AskWhyButton chart={{ chartId: 'Inflation Decomposition', selectedSeries: items.map((item) => item.category).join(', '), visibleDateRange: { start: latestDate, end: latestDate }, sourceMetadata: sources.join(', ') || 'Not available', mode: 'live' }} /><span className="rounded-full border border-white/[0.08] bg-white/[0.035] px-2.5 py-1 text-[10px] font-semibold text-slate-400">{latestDate ?? 'No validated data'}</span></div>
			</div>
			{isLoading ? <StatusState kind="loading" title="Loading decomposition" message="Checking for validated contribution data..." /> : !hasData ? <StatusState kind="empty" title="No decomposition data available" message="No validated contribution observations are connected to this view." /> : <div className="mt-3 h-[245px] w-full"><ReactECharts option={option} style={{ height: '100%', width: '100%' }} opts={{ renderer: 'svg' }} /></div>}
			<div className="mt-1 space-y-2 border-t border-white/[0.07] pt-4">{items.map((item, index) => <div key={item.category} className="flex items-center justify-between gap-3 text-xs"><span className="flex items-center gap-2 font-medium text-slate-300"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />{item.category.replace(' and beverages', '')}</span><span className="font-semibold tabular-nums text-slate-50">{Math.round(item.shareOfHeadline)}%</span></div>)}</div>
			<div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-slate-500"><span>Unit: percentage points</span>{latestDate && <span>Date: {latestDate}</span>}<span>Sources: {sources.join(', ') || 'Not available'}</span></div>
			{items.length > 0 && <details className="mt-2 text-[10px] text-slate-400"><summary className="cursor-pointer font-medium text-slate-500">View source metadata</summary><div className="mt-2 space-y-1">{items.map((item) => <a key={item.contribution.id} href={item.contribution.sourceUrl} target="_blank" rel="noreferrer" className="block hover:text-blue-700">{item.category} · {item.contribution.source} · {item.contribution.date} · confidence {Math.round(item.contribution.confidence * 100)}%</a>)}</div></details>}
		</section>
	);
}
