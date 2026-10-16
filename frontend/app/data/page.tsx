'use client';

import { useEffect, useMemo, useState } from 'react';
import { Download, Search } from 'lucide-react';
import { PageShell } from '@/components/layout';
import { getProjectSeriesCatalog, getProjectSeriesObservations, type ProjectSeriesCatalogItem } from '@/lib/research-api';

type Observation = { date: string; value: number; source: string; unit: string };
const sourceUrl: Record<string, string> = { MOSPI: 'https://mospi.gov.in/', RBI: 'https://data.rbi.org.in/', FRED: 'https://fred.stlouisfed.org/', EIA: 'https://www.eia.gov/' };
const frequencyName: Record<string, string> = { D: 'Daily', W: 'Weekly', M: 'Monthly', Q: 'Quarterly', A: 'Annual' };
const displayName = (id: string) => id.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function DataPage() {
  const [catalog, setCatalog] = useState<ProjectSeriesCatalogItem[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [observations, setObservations] = useState<Observation[]>([]);
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loadingRows, setLoadingRows] = useState(false);

  useEffect(() => { getProjectSeriesCatalog().then((items) => { setCatalog(items); setSelectedId(items.find((item) => item.available)?.id ?? items[0]?.id ?? ''); }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not load the series catalog.')); }, []);
  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    const timer = window.setTimeout(() => {
      setLoadingRows(true);
      getProjectSeriesObservations(selectedId, 500).then((rows) => { if (active) setObservations(rows); }).catch((reason: unknown) => { if (active) { setObservations([]); setError(reason instanceof Error ? reason.message : 'Could not load observations.'); } }).finally(() => { if (active) setLoadingRows(false); });
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [selectedId]);

  const filtered = useMemo(() => catalog.filter((item) => `${item.id} ${item.description} ${item.source}`.toLowerCase().includes(query.toLowerCase())), [catalog, query]);
  const selected = catalog.find((item) => item.id === selectedId);
  const download = () => {
    if (!selected) return;
    const csv = [['date', 'value', 'unit', 'source'], ...observations.map((row) => [row.date, row.value, row.unit, row.source])].map((row) => row.join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${selected.id}.csv`; anchor.click(); URL.revokeObjectURL(url);
  };

  return <PageShell title="Data Explorer" description="Browse the project series registry and the observations returned by the API.">
    <div className="space-y-5">
      <div className="rounded-xl border border-cyan-300/15 bg-cyan-400/[0.05] p-4 text-xs text-slate-300">Catalog and observations are loaded live from the project API. Only series with stored observations are marked available; this page does not fill gaps with demo data.</div>
      {error && <p className="rounded-xl border border-rose-300/20 bg-rose-400/10 px-4 py-3 text-xs text-rose-200">{error} Check the API URL and deployment access settings.</p>}
      <section className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><h2 className="text-lg font-semibold">Project series</h2><p className="mt-1 text-xs text-slate-400">{catalog.filter((item) => item.available).length} with observations · {catalog.length} registered</p></div><label className="relative"><Search size={15} className="absolute left-3 top-2.5 text-slate-400"/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search series, ID, source" className="w-full rounded-lg border border-white/10 bg-slate-950 py-2 pl-9 pr-3 text-xs sm:w-64"/></label></div></section>
      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <section className="overflow-x-auto rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><table className="w-full min-w-[650px] text-left text-xs"><thead className="text-[10px] uppercase tracking-wider text-slate-500"><tr><th className="pb-3">Series</th><th className="pb-3">Latest</th><th className="pb-3">Frequency</th><th className="pb-3">Rows</th><th className="pb-3">Status</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id} onClick={() => setSelectedId(item.id)} className={`cursor-pointer border-t border-white/[0.06] hover:bg-white/[0.04] ${selectedId === item.id ? 'bg-cyan-300/[0.06]' : ''}`}><td className="py-3 pr-3"><strong>{displayName(item.id)}</strong><p className="mt-1 text-[10px] text-slate-500">{item.id} · {item.source}</p></td><td className="py-3">{item.latest ? `${item.latest.value} ${item.unit}` : '—'}<p className="mt-1 text-[10px] text-slate-500">{item.latest?.date ?? 'No observations'}</p></td><td className="py-3 text-slate-400">{frequencyName[item.frequency] ?? item.frequency}</td><td className="py-3 text-slate-400">{item.observation_count}</td><td className="py-3"><span className={item.available ? 'text-emerald-300' : 'text-slate-500'}>{item.available ? 'Available' : 'No data'}</span></td></tr>)}</tbody></table>{filtered.length === 0 && <p className="py-8 text-center text-xs text-slate-500">No registered series match.</p>}</section>
        {selected && <aside className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] uppercase tracking-wider text-cyan-300">Series details</p><h2 className="mt-1 text-lg font-semibold">{displayName(selected.id)}</h2></div><button disabled={!observations.length} onClick={download} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold disabled:opacity-40"><Download size={14}/>CSV</button></div><p className="mt-3 text-xs leading-5 text-slate-400">{selected.description}</p><dl className="mt-4 space-y-2 border-y border-white/[0.07] py-3 text-xs"><div className="flex justify-between"><dt className="text-slate-500">Source</dt><dd><a href={sourceUrl[selected.source] ?? '#'} target="_blank" rel="noreferrer">{selected.source}</a></dd></div><div className="flex justify-between"><dt className="text-slate-500">Unit / base</dt><dd>{selected.unit} · {selected.base_year ?? 'not specified'}</dd></div><div className="flex justify-between"><dt className="text-slate-500">Latest observation</dt><dd>{selected.latest?.date ?? '—'}</dd></div><div className="flex justify-between"><dt className="text-slate-500">Observation count</dt><dd>{selected.observation_count}</dd></div></dl><h3 className="mt-4 text-xs font-semibold">Latest observations</h3><div className="mt-2 max-h-80 space-y-1 overflow-auto">{loadingRows ? <p className="text-xs text-slate-500">Loading observations…</p> : observations.slice(-30).reverse().map((row) => <div key={row.date} className="flex justify-between rounded bg-white/[0.03] px-3 py-2 text-xs"><span className="text-slate-400">{row.date}</span><strong>{row.value} {row.unit}</strong></div>)}</div></aside>}
      </div>
    </div>
  </PageShell>;
}
