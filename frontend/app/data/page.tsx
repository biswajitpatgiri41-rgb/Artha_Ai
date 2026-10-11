'use client';

import { Download, FileSearch, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { SourceBadge } from '@/components';
import { PageShell } from '@/components/layout';
import { MOCK_DATA_NOTICE, mockSeriesCatalog } from '@/lib/mock-data';
import type { MacroSeries } from '@/lib/types';
import { getProjectSeriesCatalog, getProjectSeriesObservations } from '@/lib/research-api';

function csvCell(value: string | number | null) {
	const text = value === null ? '' : String(value);
	return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function downloadSeries(series: MacroSeries) {
	const header = ['date', 'value', 'unit', 'source', 'status'];
	const rows = series.observations.map((observation) => [observation.date, observation.value, series.unit, series.source, series.isMock ? 'mock' : 'archived_package']);
	const csv = [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\n');
	const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
	const anchor = document.createElement('a');
	anchor.href = url;
	anchor.download = `${series.id}.csv`;
	anchor.click();
	URL.revokeObjectURL(url);
}

export default function DataPage() {
	const [seriesCatalog, setSeriesCatalog] = useState<MacroSeries[]>(mockSeriesCatalog);
	const [dataMode, setDataMode] = useState<'loading' | 'package' | 'mock'>('loading');
	const [query, setQuery] = useState('');
	const [sourceFilter, setSourceFilter] = useState('All sources');
	const [selectedId, setSelectedId] = useState(mockSeriesCatalog[0]?.id ?? '');
	useEffect(() => {
		let active = true;
		Promise.all([getProjectSeriesCatalog(), getProjectSeriesObservations('cpi_yoy', 500)])
			.then(([catalog, observations]) => {
				if (!active) return;
				const available = catalog.find((series) => series.id === 'cpi_yoy' && series.available);
				if (!available || observations.length === 0) {
					setDataMode('mock');
					return;
				}
				const template = mockSeriesCatalog.find((series) => series.id === 'india-cpi-headline');
				if (!template) {
					setDataMode('mock');
					return;
				}
				const latest = observations[observations.length - 1];
				const packageSeries: MacroSeries = {
					...template,
					id: 'cpi_yoy',
					name: 'India headline CPI inflation (2024 base)',
					description: 'Observed MoSPI 2024-base CPI year-over-year target from the versioned final model package. The bundle is a static data vintage.',
					latestValue: latest.value,
					unit: '% year-over-year',
					source: 'MoSPI',
					baseYear: '2024',
					latestObservation: latest.date,
					status: 'archived',
					retrievedDate: 'Not refreshed; bundled package snapshot',
					observations: observations.map(({ date, value }) => ({ date, value })),
					isMock: false,
				};
				setSeriesCatalog([packageSeries, ...mockSeriesCatalog.filter((series) => series.id !== 'india-cpi-headline')]);
				setSelectedId((current) => current === 'india-cpi-headline' ? 'cpi_yoy' : current);
				setDataMode('package');
			})
			.catch(() => { if (active) setDataMode('mock'); });
		return () => { active = false; };
	}, []);
	const sources = ['All sources', ...new Set(seriesCatalog.map((series) => series.source))];
	const filteredSeries = useMemo(() => seriesCatalog.filter((series) => {
		const matchesQuery = `${series.name} ${series.id} ${series.description}`.toLowerCase().includes(query.toLowerCase());
		return matchesQuery && (sourceFilter === 'All sources' || series.source === sourceFilter);
	}), [seriesCatalog, query, sourceFilter]);
	const selected = seriesCatalog.find((series) => series.id === selectedId) ?? filteredSeries[0] ?? seriesCatalog[0];

	return (
		<PageShell title="Data Explorer" description="Inspect the bundled CPI dataset and mock fallback series used by the research workspace.">
			<div className="space-y-6">
				<div className="flex items-start gap-3 rounded-2xl border border-amber-300/15 bg-amber-400/[0.07] px-4 py-3 text-xs text-amber-100"><FileSearch size={17} className="mt-0.5 shrink-0 text-amber-300" /><span><strong>{dataMode === 'package' ? 'BUNDLED CPI DATA + MOCK FALLBACK' : dataMode === 'loading' ? 'LOADING PROJECT DATA' : 'MOCK DATA CATALOG'}</strong><span className="ml-2 text-amber-200/70">{dataMode === 'package' ? 'MoSPI CPI observations are loaded from the checksum-verified package. Other unavailable series stay mock.' : MOCK_DATA_NOTICE}</span></span></div>

				<section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-700">Series registry</p><h2 className="mt-1 text-lg font-semibold text-slate-950">Macroeconomic series</h2><p className="mt-1 text-xs text-slate-500">Search, filter, inspect, and export the current demo catalog.</p></div><div className="flex flex-col gap-2 sm:flex-row"><label className="relative"><span className="sr-only">Search series</span><Search size={15} className="pointer-events-none absolute left-3 top-2.5 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search series or ID" className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-xs outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 sm:w-56" /></label><label><span className="sr-only">Filter by source</span><select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"><option>All sources</option>{sources.slice(1).map((source) => <option key={source}>{source}</option>)}</select></label></div></div></section>

				<div className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
					<section className="min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><div className="mb-4 flex items-center justify-between"><p className="text-xs font-semibold text-slate-700">{filteredSeries.length} series shown</p><span className="text-[10px] uppercase tracking-[0.1em] text-slate-400">{seriesCatalog.filter((series) => !series.isMock).length} bundled ? {seriesCatalog.filter((series) => series.isMock).length} mock</span></div><div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-xs"><thead className="border-b border-slate-200 text-[10px] uppercase tracking-[0.12em] text-slate-400"><tr><th className="pb-3 font-semibold">Series</th><th className="pb-3 font-semibold">Latest value</th><th className="pb-3 font-semibold">Unit</th><th className="pb-3 font-semibold">Frequency</th><th className="pb-3 font-semibold">Source</th><th className="pb-3 font-semibold">Base year</th><th className="pb-3 font-semibold">Latest observation</th><th className="pb-3 font-semibold">Status</th></tr></thead><tbody className="divide-y divide-slate-100">{filteredSeries.map((series) => <tr key={series.id} onClick={() => setSelectedId(series.id)} className={`cursor-pointer transition hover:bg-blue-50/50 ${selected?.id === series.id ? 'bg-blue-50/70' : ''}`}><td className="py-3 pr-3"><p className="font-semibold text-slate-800">{series.name}</p><p className="mt-1 text-[10px] text-slate-400">{series.id}</p></td><td className="py-3 font-semibold text-slate-900">{series.latestValue}</td><td className="py-3 text-slate-500">{series.unit}</td><td className="py-3 text-slate-500">{series.frequency}</td><td className="py-3"><SourceBadge source={series.source} /></td><td className="py-3 text-slate-500">{series.baseYear ?? '—'}</td><td className="py-3 text-slate-500">{series.latestObservation}</td><td className="py-3"><span className={`rounded-md px-2 py-1 text-[10px] font-semibold ${series.isMock ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'}`}>{series.isMock ? 'Mock' : 'Archived package'}</span></td></tr>)}</tbody></table>{filteredSeries.length === 0 && <div className="py-14 text-center text-xs text-slate-400">No series match the current filters.</div>}</div></section>

					{selected && <aside className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-700">Series details</p><h2 className="mt-1 text-lg font-semibold text-slate-950">{selected.name}</h2></div><button type="button" onClick={() => downloadSeries(selected)} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-blue-700"><Download size={14} />Download CSV</button></div><p className="mt-4 text-xs leading-5 text-slate-600">{selected.description}</p><dl className="mt-5 divide-y divide-slate-100 border-y border-slate-100">{[['Series ID', selected.id], ['Source', selected.source], ['Frequency', selected.frequency], ['Unit', selected.unit], ['Base year', selected.baseYear ?? 'Not applicable'], ['Seasonal adjustment', selected.seasonalAdjustment], ['Latest observation', selected.latestObservation], ['Retrieved date', selected.retrievedDate], ['Status', selected.isMock ? 'Mock demo' : 'Archived package snapshot']].map(([label, value]) => <div key={label} className="flex items-start justify-between gap-4 py-3 text-xs"><dt className="text-slate-400">{label}</dt><dd className="max-w-[60%] text-right font-medium text-slate-700">{label === 'Source' ? <a href={selected.sourceUrl} target="_blank" rel="noreferrer" className="text-blue-700 hover:underline">{value}</a> : value}</dd></div>)}</dl><div className="mt-5"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">Observation preview</p><div className="mt-3 space-y-2">{selected.observations.map((observation) => <div key={observation.date} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-xs"><span className="text-slate-500">{observation.date}</span><strong className="text-slate-800">{observation.value} {selected.unit}</strong></div>)}</div></div></aside>}
				</div>
			</div>
		</PageShell>
	);
}
