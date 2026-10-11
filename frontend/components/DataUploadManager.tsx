'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Database, Upload } from 'lucide-react';

type DataSection = {
	id: string; name: string; source: string; notes: string; required_for_mvp: boolean;
	frequency: string; unit: string; base_year: string | null; available: boolean;
	observation_count: number; start_date: string | null; end_date: string | null; minimum_months: number | null;
};
type RequirementsResponse = {
	readiness: { headline_index_months: number; derived_yoy_months: number; minimum_training_months: number; status: string };
	upload_schema: { required_columns: string[]; optional_columns: string[]; max_file_bytes: number; update_mode: string };
	sections: DataSection[];
};

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export function DataUploadManager() {
	const [data, setData] = useState<RequirementsResponse | null>(null);
	const [files, setFiles] = useState<Record<string, File>>({});
	const [mode, setMode] = useState<'upsert' | 'replace'>('upsert');
	const [busy, setBusy] = useState<string | null>(null);
	const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);
	const [demoHref, setDemoHref] = useState<string | null>(null);
	const [demoInfo, setDemoInfo] = useState('');

	const refresh = async () => {
		const response = await fetch(`${API}/data/requirements`, { cache: 'no-store' });
		if (!response.ok) throw new Error('Could not load data requirements from the backend.');
		setData(await response.json() as RequirementsResponse);
	};
	useEffect(() => {
		let live = true;
		fetch(`${API}/data/requirements`, { cache: 'no-store' })
			.then((response) => response.ok ? response.json() : Promise.reject(new Error('API offline')))
			.then((payload: RequirementsResponse) => { if (live) setData(payload); })
			.catch(() => { if (live) setMessage({ kind: 'error', text: 'Backend unavailable. Start the FastAPI service to manage project data.' }); });
		fetch(`${API}/data/demo/repo-rate`, { cache: 'no-store' })
			.then(async (response) => {
				if (!response.ok) return;
				const text = await response.text();
				const rows = text.trim().split(/\r?\n/);
				if (live) { setDemoInfo(`${Math.max(0, rows.length - 1)} simulated monthly rows`); setDemoHref(URL.createObjectURL(new Blob([text], { type: 'text/csv' }))); }
			});
		return () => { live = false; };
	}, []);
	const groups = useMemo(() => [
		{ title: 'Core forecasting inputs', rows: data?.sections.filter((item) => item.required_for_mvp) ?? [] },
		{ title: 'Optional and context data', rows: data?.sections.filter((item) => !item.required_for_mvp) ?? [] },
	], [data]);

	const upload = async (section: DataSection) => {
		const file = files[section.id];
		if (!file) return;
		setBusy(section.id); setMessage(null);
		try {
			const response = await fetch(`${API}/data/upload/${encodeURIComponent(section.id)}?mode=${mode}`, {
				method: 'POST', headers: { 'X-Filename': file.name, 'Content-Type': 'application/octet-stream' }, body: file,
			});
			const result = await response.json();
			if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Upload failed validation.');
			setMessage({ kind: 'ok', text: `${section.name}: imported ${result.uploaded_observations} observations; ${result.total_observations} dates now in the series.` });
			setFiles((current) => { const next = { ...current }; delete next[section.id]; return next; });
			await refresh();
		} catch (error) {
			setMessage({ kind: 'error', text: error instanceof Error ? error.message : 'Upload failed.' });
		} finally { setBusy(null); }
	};

	return <section className="space-y-5 rounded-2xl border border-blue-200 bg-white p-5 shadow-sm shadow-slate-200/40 sm:p-6">
		<div className="flex flex-wrap items-start justify-between gap-4">
			<div><p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-700"><Database size={14} /> Project data management</p><h2 className="mt-1 text-lg font-semibold text-slate-950">Upload and update datasets</h2><p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">Upload one series at a time as CSV or Excel. Use columns <code>date,value</code>; optional columns are <code>release_date,source,unit,base_year</code>. Original files are retained with a checksum.</p></div>
			<label className="text-xs text-slate-600">When dates already exist<select value={mode} onChange={(event) => setMode(event.target.value as 'upsert' | 'replace')} className="mt-1 block rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs"><option value="upsert">Update matching dates and add new dates</option><option value="replace">Replace this series history</option></select></label>
		</div>
		{data && <div className={`flex items-start gap-3 rounded-xl border p-3 ${data.readiness.status === 'not_ready' ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-emerald-200 bg-emerald-50 text-emerald-900'}`}><AlertTriangle size={16} className="mt-0.5 shrink-0" /><p className="text-xs leading-5"><strong>Training readiness: {data.readiness.status === 'not_ready' ? 'not ready' : 'initial dataset available'}.</strong> Current headline CPI index has {data.readiness.headline_index_months} monthly observations and yields {data.readiness.derived_yoy_months} usable YoY target months; project guidance asks for at least {data.readiness.minimum_training_months}. Synthetic demo data is excluded from this count.</p></div>}
		{message && <div role="status" className={`rounded-lg px-3 py-2 text-xs ${message.kind === 'ok' ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'}`}>{message.text}</div>}
		{groups.map((group) => <div key={group.title}><h3 className="mb-2 text-sm font-semibold text-slate-800">{group.title}</h3><div className="grid gap-3 lg:grid-cols-2">{group.rows.map((section) => <article key={section.id} className="rounded-xl border border-slate-200 p-4">
			<div className="flex items-start justify-between gap-3"><div><h4 className="text-sm font-semibold text-slate-900">{section.name}</h4><p className="mt-0.5 text-[10px] text-slate-500">{section.id} · {section.source} · {section.frequency} · {section.unit}{section.base_year ? ` · base ${section.base_year}` : ''}</p><p className="mt-2 text-[11px] leading-4 text-slate-500">{section.notes}</p></div><span className={`shrink-0 rounded-full px-2 py-1 text-[9px] font-semibold ${section.available ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{section.available ? `${section.observation_count} rows` : 'Missing'}</span></div>
			{section.start_date && <p className="mt-2 text-[10px] text-slate-400">{section.start_date} → {section.end_date}</p>}
			<div className="mt-3 flex flex-wrap items-center gap-2"><input aria-label={`Choose file for ${section.name}`} type="file" accept=".csv,.xlsx,.xlsm" onChange={(event) => { const selected = event.target.files?.[0]; if (selected) setFiles((current) => ({ ...current, [section.id]: selected })); }} className="min-w-0 flex-1 text-[10px] text-slate-600 file:mr-2 file:rounded-md file:border-0 file:bg-blue-50 file:px-2 file:py-1.5 file:text-[10px] file:font-semibold file:text-blue-700" />
			<button type="button" disabled={!files[section.id] || busy !== null} onClick={() => void upload(section)} className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-[10px] font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"><Upload size={13} />{busy === section.id ? 'Uploading…' : 'Upload'}</button></div>
			</article>)}</div></div>)}
		<div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed border-violet-300 bg-violet-50/70 p-4"><div className="flex gap-2"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-violet-700" /><div><p className="text-xs font-semibold text-violet-950">Simulated RBI sandbox series — not real RBI data</p><p className="mt-1 text-[10px] text-violet-800">{demoInfo || 'Preview only. It is stored under data/demo and never enters forecasts or model training.'} · excluded from canonical observations and all readiness counts.</p></div></div>{demoHref && <a href={demoHref} download="synthetic_repo_rate_preview.csv" className="rounded-lg border border-violet-200 bg-white px-3 py-2 text-[10px] font-semibold text-violet-800">Download demo CSV</a>}</div>
		<p className="text-[10px] leading-4 text-slate-400">CSV date format: YYYY-MM-DD or DD/MM/YYYY. Dates within each upload must be unique and values numeric. Upsert is the safe ongoing-update mode; Replace changes the active history while keeping prior raw files for audit. Max upload: {data ? Math.round(data.upload_schema.max_file_bytes / 1024 / 1024) : 20} MB.</p>
	</section>;
}
