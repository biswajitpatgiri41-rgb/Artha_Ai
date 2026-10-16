'use client';

import type { MacroObservation } from '@/lib/types';
import type { ForecastPoint, TimeSeriesPoint } from '@/lib/types';
import { StatusState } from './ui';
import ReactECharts from 'echarts-for-react';
import { AskWhyButton } from './assistant/AskWhyButton';

interface MacroChartProps {
	observations: MacroObservation[];
	historical: TimeSeriesPoint[];
	forecast: ForecastPoint[];
	isLoading?: boolean;
}

export function MacroChart({ observations, historical, forecast, isLoading = false }: MacroChartProps) {
	const hasData = historical.length > 0 || forecast.length > 0;
	const actualValues = historical.map((point) => [point.date, point.value]);
	const forecastValues = forecast.map((point) => [point.date, point.value]);
	const lowerValues = forecast.map((point) => [point.date, point.lowerBound]);
	const upperValues = forecast.map((point) => [point.date, point.upperBound]);
	const sourceObservations = [...historical, ...forecast];
	const sourceNames = [...new Set(sourceObservations.map((point) => point.source))];
	const latestDate = sourceObservations.at(-1)?.date;
	const chartValues = [
		...historical.map((point) => point.value),
		...forecast.flatMap((point) => [point.value, point.lowerBound, point.upperBound]),
	];
	const chartMin = chartValues.length ? Math.floor(Math.min(...chartValues) - 0.5) : 0;
	const chartMax = chartValues.length ? Math.ceil(Math.max(...chartValues) + 0.5) : 10;

	const option = {
		animation: false,
		grid: { left: 8, right: 16, top: 38, bottom: 18, containLabel: true },
		legend: { top: 0, right: 0, itemWidth: 12, itemHeight: 7, textStyle: { color: '#94a3b8', fontSize: 10 } },
		tooltip: {
			trigger: 'axis',
			backgroundColor: 'rgba(7, 20, 38, 0.94)',
			borderColor: 'rgba(255,255,255,0.12)',
			textStyle: { color: '#f8fafc', fontSize: 11 },
			valueFormatter: (value: number) => `${value.toFixed(1)}%`,
			axisPointer: { type: 'line', lineStyle: { color: '#64748b', type: 'dashed' } },
		},
		xAxis: { type: 'time', boundaryGap: false, axisLine: { lineStyle: { color: 'rgba(148,163,184,0.22)' } }, axisLabel: { color: '#64748b', fontSize: 10, hideOverlap: true, formatter: '{MMM}\n{yyyy}' } },
		yAxis: { type: 'value', min: chartMin, max: chartMax, splitNumber: 4, axisLabel: { color: '#64748b', fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.1)' } } },
		series: [
			{ name: 'Lower bound', type: 'line', data: lowerValues, stack: 'forecast-band', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false } },
			{ name: 'Uncertainty band', type: 'line', data: upperValues, stack: 'forecast-band', symbol: 'none', lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(37, 99, 235, 0.14)' }, tooltip: { show: false } },
			{ name: 'Historical actual', type: 'line', data: actualValues, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2.5, color: '#0f5ed7' }, itemStyle: { color: '#0f5ed7', borderColor: '#fff', borderWidth: 2 } },
			{ name: 'Stored model forecast', type: 'line', data: forecastValues, symbol: 'circle', symbolSize: 5, lineStyle: { width: 2, type: 'dashed', color: '#d48a16' }, itemStyle: { color: '#d48a16' } },
		],
	};

	return (
		<section className="rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.25)] backdrop-blur-2xl">
			<div className="flex items-start justify-between gap-4">
				<div>
					<div className="flex items-center gap-2">
						<span className="h-2 w-2 rounded-full bg-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.7)]" />
						<h2 className="text-base font-semibold text-slate-50">CPI Inflation Trend</h2>
					</div>
					<p className="mt-1 text-xs text-slate-400">Validated historical actuals with stored model forecast</p>
				</div>
				<div className="flex items-center gap-2"><AskWhyButton chart={{ chartId: 'CPI Inflation Trend', selectedSeries: 'CPI inflation', visibleDateRange: { start: historical[0]?.date, end: historical.at(-1)?.date }, sourceMetadata: sourceNames.join(', ') || 'Not available', mode: 'live' }} /><span className="rounded-full border border-amber-300/15 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold text-amber-300">Stored forecast</span></div>
			</div>
			{isLoading ? <StatusState kind="loading" title="Loading CPI observations" message="Reading validated project data..." /> : !hasData ? <StatusState kind="empty" title="No CPI observations available" message="No validated historical or forecast observations are connected to this view." /> : <div className="mt-4 h-[320px] w-full sm:h-[350px]"><ReactECharts option={option} style={{ height: '100%', width: '100%' }} opts={{ renderer: 'svg' }} /></div>}
			<div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.07] pt-3 text-[10px] text-slate-500">
				<span>{observations.length} macro observations · unit: % year-on-year</span>
				{latestDate && <span>Latest: {latestDate}</span>}
				<span>Sources: {sourceNames.join(', ') || 'Not available'}</span>
			</div>
			{sourceObservations.length > 0 && <details className="mt-2 text-[10px] text-slate-400"><summary className="cursor-pointer font-medium text-slate-500">View source metadata</summary><div className="mt-2 grid gap-1 sm:grid-cols-2">{sourceObservations.map((point) => <a key={point.id} href={point.sourceUrl} target="_blank" rel="noreferrer" className="truncate hover:text-blue-700">{point.period} · {point.source} · {point.date}</a>)}</div></details>}
		</section>
	);
}
