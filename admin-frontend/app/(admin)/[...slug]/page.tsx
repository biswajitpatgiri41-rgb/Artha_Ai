'use client';

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Activity, AlertTriangle, ArrowUpRight, CheckCircle2, ChevronRight, FileUp, RefreshCw, Search, Trash2 } from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
type Json = Record<string, unknown>;
type Action = { label: string; method: 'GET' | 'POST'; path: string; body?: Json };

const TITLES: Record<string, string> = {
  'system-health': 'System Health', infrastructure: 'Infrastructure', services: 'Services',
  'data-health': 'Data Health', 'data-pipeline': 'Data Pipeline', 'data-versions': 'Data Versions',
  'data-validation': 'Data Validation', models: 'Model Registry', 'model-drift': 'Model Drift',
  experiments: 'Experiments', deployments: 'Deployments', 'inference-logs': 'Inference Logs',
  'agent-status': 'Agent Status', 'agent-executions': 'Agent Executions',
  'knowledge-base': 'Knowledge Base', documents: 'Documents', index: 'Index Status',
  'forecast-operations': 'Forecast Operations', 'scenario-engine': 'Scenario Engine',
  security: 'Security Events', users: 'Users', 'audit-logs': 'Audit Logs',
  incidents: 'Incidents', notifications: 'Notifications', 'background-jobs': 'Background Jobs',
  settings: 'Settings', activity: 'Recent Activity',
};

function plan(slug: string[]): { endpoints: string[]; actions?: Action[]; note?: string } {
  const page = slug[0] || '';
  if (['system-health', 'infrastructure', 'services'].includes(page)) return { endpoints: ['/api/admin/health', '/api/admin/metrics'], note: 'Process and HTTP telemetry from this FastAPI instance. Host metrics may be unavailable if psutil is not installed.' };
  if (['data-health', 'data-validation'].includes(page)) return { endpoints: ['/data-quality', '/data/requirements', '/sources'], note: 'Quality is derived from local catalog and ingestion manifests; it does not probe upstream provider availability.' };
  if (['data-pipeline', 'data-versions'].includes(page)) return { endpoints: ['/data/requirements', '/series'], note: 'Inspect canonical series readiness and current observation vintages. Data ingestion is not triggered automatically from this page.' };
  if (page === 'models') return { endpoints: ['/models/registry', '/forecast/final/models', '/forecast/models'], note: 'Registry data is read from installed, checksum-validated artifacts. No model is automatically promoted.' };
  if (['model-drift', 'experiments', 'deployments'].includes(page)) return { endpoints: ['/models/registry'], note: 'Drift monitoring, experiment tracking, and deployment controls require registered model evaluation services; this project currently exposes artifact registry metadata only.' };
  if (page === 'inference-logs') return { endpoints: ['/research?limit=50'], note: 'These are persisted research executions, not a separate production inference log stream.' };
  if (['agent-status', 'agent-executions'].includes(page)) return { endpoints: ['/research?limit=50', '/health'], note: 'The project API currently persists prototype research runs; live LangGraph agent execution telemetry is not exposed as an operational endpoint.' };
  if (['knowledge-base', 'documents', 'index'].includes(page)) return { endpoints: [], note: 'Evidence is scoped to a run. Select or create a run below to inspect and manage its uploaded files.' };
  if (page === 'forecast-operations') return { endpoints: ['/forecast/final/models', '/series'], actions: [{ label: 'Run 6-step final forecast', method: 'GET', path: '/forecast/final?model=ensemble&horizon=6' }, { label: 'Run rolling backtest', method: 'GET', path: '/backtest?series_id=cpi_yoy&horizon=1&min_train=24' }], note: 'Forecast and backtest use project data and registered deterministic models. Errors are shown as returned by the API.' };
  if (page === 'scenario-engine') return { endpoints: ['/series'], actions: [{ label: 'Run baseline scenario', method: 'POST', path: '/simulate', body: { base_inflation: 5, oil_change_pct: 0, inr_change_pct: 0, food_shock_pp: 0, repo_change_bp: 0, horizon_months: 6 } }], note: 'Scenario output comes from the existing deterministic scenario function. Adjust the request payload in the JSON controls below before running.' };
  if (['security', 'users', 'audit-logs'].includes(page)) return { endpoints: ['/api/admin/health'], note: 'No admin user-management, security-event, or immutable audit-log API is configured. This screen reports that capability gap rather than inventing records.' };
  if (['incidents', 'notifications', 'background-jobs'].includes(page)) return { endpoints: ['/api/admin/health', '/api/admin/activity'], note: 'Incident workflow, notification delivery, and background job queue services are not configured; recent API events are shown where available.' };
  if (page === 'settings') return { endpoints: ['/health', '/evidence/config'], note: 'Runtime settings shown here are non-secret API status and evidence limits. Secret values are never returned.' };
  return { endpoints: ['/api/admin/activity'], note: 'Recent API activity captured by the local telemetry middleware.' };
}

function pretty(value: unknown) { return JSON.stringify(value, null, 2); }
function displayValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return Array.isArray(value) ? `${value.length} items` : 'Details';
  return String(value);
}

export default function AdminModulePage({ params }: { params: Promise<{ slug: string[] }> }) {
  const [slug, setSlug] = useState<string[]>([]);
  const [data, setData] = useState<Record<string, Json | string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionResult, setActionResult] = useState<unknown>(null);
  const [query, setQuery] = useState('');
  const [runId, setRunId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [searchResults, setSearchResults] = useState<Json | null>(null);
  const [scenarioBody, setScenarioBody] = useState(pretty({ base_inflation: 5, oil_change_pct: 0, inr_change_pct: 0, food_shock_pp: 0, repo_change_bp: 0, horizon_months: 6 }));
  const spec = useMemo(() => plan(slug), [slug]);
  const title = slug.map((part) => TITLES[part] ?? part.replace(/-/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())).join(' / ') || 'Recent Activity';

  useEffect(() => {
    const timer = window.setTimeout(() => { void params.then((value) => setSlug(value.slug)); }, 0);
    return () => window.clearTimeout(timer);
  }, [params]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      let id = window.localStorage.getItem('admin_evidence_run_id');
      if (!id) { id = window.crypto.randomUUID(); window.localStorage.setItem('admin_evidence_run_id', id); }
      setRunId(id);
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const refresh = useCallback(async () => {
    if (!slug.length) return;
    setLoading(true); setError('');
    const results: Record<string, Json | string> = {};
    await Promise.all(spec.endpoints.map(async (path) => {
      try {
        const response = await fetch(`${API}${path}`, { cache: 'no-store' });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(`${response.status}: ${typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body)}`);
        results[path] = body;
      } catch (reason) { results[path] = reason instanceof Error ? reason.message : 'Request failed'; }
    }));
    if (['knowledge-base', 'documents', 'index'].includes(slug[0]) && runId) {
      try {
        const response = await fetch(`${API}/evidence/run/${runId}`, { cache: 'no-store' });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
        results[`/evidence/run/${runId}`] = body;
      } catch (reason) { results[`/evidence/run/${runId}`] = reason instanceof Error ? reason.message : 'Request failed'; }
    }
    setData(results); setLoading(false);
  }, [slug, spec.endpoints, runId]);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  const runAction = async (action: Action) => {
    setError(''); setActionResult(null); setLoading(true);
    try {
      const path = action.path === '/simulate' ? action.path : action.path;
      const body = action.path === '/simulate' ? JSON.parse(scenarioBody) : action.body;
      const response = await fetch(`${API}${path}`, { method: action.method, headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(result.detail || result)}`);
      setActionResult(result);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Operation failed'); }
    finally { setLoading(false); }
  };

  const uploadEvidence = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !runId) return;
    setUploading(true); setError(''); setActionResult(null);
    const form = new FormData(); form.append('file', file); form.append('run_id', runId); form.append('lifecycle', 'TEMPORARY');
    try {
      const response = await fetch(`${API}/evidence/upload`, { method: 'POST', body: form });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(result.detail || result)}`);
      setActionResult(result); setFile(null); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Upload failed'); }
    finally { setUploading(false); }
  };

  const deleteEvidence = async (evidenceId: string) => {
    if (!runId) return;
    try {
      const response = await fetch(`${API}/evidence/${encodeURIComponent(evidenceId)}?run_id=${encodeURIComponent(runId)}`, { method: 'DELETE' });
      if (!response.ok) throw new Error((await response.text()) || `Request failed (${response.status})`);
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Delete failed'); }
  };

  const searchEvidence = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setSearchResults(null);
    try {
      const response = await fetch(`${API}/evidence/search`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ run_id: runId, query, top_k: 5 }) });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(`${response.status}: ${JSON.stringify(body.detail || body)}`);
      setSearchResults(body);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Evidence search failed'); }
  };

  const isEvidence = ['knowledge-base', 'documents', 'index'].includes(slug[0]);
  const evidenceListing = Object.entries(data).find(([path]) => path.startsWith('/evidence/run/'))?.[1] as Json | string | undefined;
  const files = (typeof evidenceListing === 'object' && evidenceListing ? evidenceListing.evidence : []) as Json[];

  useEffect(() => {
    if (slug[0] !== 'settings') return;
    let cancelled = false;
    fetch(`${API}/evidence/config`, { cache: 'no-store' }).then((response) => response.json()).then((result) => { if (!cancelled) setData((current) => ({ ...current, '/evidence/config': result })); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [slug]);

  const onFile = (event: ChangeEvent<HTMLInputElement>) => setFile(event.target.files?.[0] ?? null);
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="admin-terminal-heading">{title.toUpperCase()}</p><p className="text-admin-text-secondary mt-2">Live operations console connected to configured project APIs.</p></div>
        <button onClick={() => void refresh()} disabled={loading} className="admin-btn-secondary inline-flex items-center gap-2"><RefreshCw size={15} className={loading ? 'animate-spin' : ''} />Refresh data</button>
      </div>
      {spec.note && <div className="admin-card p-4 flex gap-3 text-sm text-admin-text-secondary"><Activity className="text-admin-neon-green shrink-0" size={18} /><span>{spec.note}</span></div>}
      {error && <div role="alert" className="admin-card p-4 border-rose-500/40 bg-rose-500/5 text-rose-300 flex gap-2"><AlertTriangle size={18} />{error}</div>}
      {spec.actions?.some((action) => action.path === '/simulate') && <section className="admin-card p-5 space-y-3"><h2 className="font-mono text-sm">SCENARIO INPUTS</h2><p className="text-xs text-admin-text-muted">Edit the exact request sent to the existing scenario engine.</p><textarea value={scenarioBody} onChange={(event) => setScenarioBody(event.target.value)} rows={6} className="w-full rounded-lg bg-admin-bg border border-admin-border p-3 font-mono text-xs text-admin-text-primary" /><button onClick={() => void runAction(spec.actions![0])} disabled={loading} className="admin-btn-primary">Run deterministic scenario</button></section>}
      {spec.actions && spec.actions.filter((action) => action.path !== '/simulate').length > 0 && <section className="admin-card p-5"><h2 className="font-mono text-sm mb-3">AVAILABLE OPERATIONS</h2><div className="flex flex-wrap gap-3">{spec.actions.filter((action) => action.path !== '/simulate').map((action) => <button key={action.label} onClick={() => void runAction(action)} disabled={loading} className="admin-btn-secondary inline-flex items-center gap-2">{action.label}<ArrowUpRight size={14} /></button>)}</div></section>}
      {isEvidence && <>
        <section className="admin-card p-5"><div className="flex flex-wrap justify-between gap-2"><div><h2 className="font-mono text-sm">CURRENT LOCAL RUN</h2><p className="text-xs text-admin-text-muted mt-1">Temporary evidence is scoped to this browser run ID.</p></div><code className="text-xs text-admin-neon-green break-all">{runId || 'Creating run…'}</code></div>
          <form onSubmit={uploadEvidence} className="mt-4 flex flex-wrap items-center gap-3"><label className="admin-btn-secondary inline-flex items-center gap-2 cursor-pointer"><FileUp size={16} />Browse evidence<input type="file" accept=".pdf,.csv,.xlsx,.json,.txt,.md" onChange={onFile} className="sr-only" /></label><span className="text-xs text-admin-text-secondary">{file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : 'PDF, CSV, XLSX, JSON, TXT, MD'}</span><button type="submit" disabled={!file || uploading} className="admin-btn-primary">{uploading ? 'Uploading…' : 'Upload'}</button></form>
          <p className="text-[11px] text-admin-text-muted mt-3">Files go to the configured evidence service. No successful processing is implied if the backend or parser returns an error. Local development has no user authentication; this run ID is not multi-tenant security.</p>
        </section>
        <section className="admin-card p-5"><div className="flex items-center justify-between mb-4"><h2 className="font-mono text-sm">UPLOADED EVIDENCE <span className="text-admin-text-muted">({files.length})</span></h2><button className="text-admin-neon-green text-xs" onClick={() => void refresh()}>Refresh list</button></div>
          {typeof evidenceListing === 'string' && <p className="text-sm text-admin-amber">{evidenceListing}</p>}
          {files.length === 0 ? <p className="text-sm text-admin-text-muted">No evidence uploaded to this run yet.</p> : <div className="space-y-2">{files.map((item) => <div key={String(item.evidence_id)} className="rounded-lg border border-admin-border bg-admin-bg-secondary/50 p-3 flex flex-wrap items-center gap-3"><CheckCircle2 size={17} className="text-admin-neon-green" /><div className="min-w-0 flex-1"><p className="text-sm truncate">{String(item.original_filename ?? 'Evidence file')}</p><p className="text-xs text-admin-text-muted">{String(item.format ?? 'unknown')} · {Number(item.size || 0).toLocaleString()} bytes · {String(item.status ?? 'unknown')} · {String(item.indexed_chunks ?? '—')} chunks</p></div><button onClick={() => window.alert(pretty(item))} className="admin-btn-secondary text-xs">Metadata</button><button onClick={() => void deleteEvidence(String(item.evidence_id))} className="admin-btn-secondary text-rose-300" aria-label={`Remove ${String(item.original_filename ?? 'evidence')}`}><Trash2 size={15} /></button></div>)}</div>}
        </section>
        <section className="admin-card p-5"><h2 className="font-mono text-sm mb-3">EVIDENCE SEARCH</h2><form onSubmit={searchEvidence} className="flex gap-2"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search uploaded PDF, TXT, or MD evidence" className="flex-1 rounded-lg bg-admin-bg border border-admin-border px-3 py-2 text-sm" /><button disabled={!query.trim()} className="admin-btn-primary inline-flex items-center gap-2"><Search size={15} />Search</button></form>{searchResults && <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-admin-bg p-3 text-xs text-admin-text-secondary">{pretty(searchResults)}</pre>}</section>
      </>}
      {Object.entries(data).filter(([path]) => !path.startsWith('/evidence/run/')).map(([path, value]) => <DataPanel key={path} title={path} value={value} query={query} setQuery={setQuery} />)}
      {actionResult !== null && <section className="admin-card p-5"><h2 className="font-mono text-sm mb-3">OPERATION RESULT</h2><pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-xs text-admin-text-secondary">{pretty(actionResult)}</pre></section>}
      {!loading && Object.keys(data).length === 0 && !isEvidence && <div className="admin-card p-8 text-center text-sm text-admin-text-muted">No API data returned. Check that the FastAPI server is running at <code>{API}</code>.</div>}
      <div className="text-[11px] text-admin-text-muted flex items-center gap-2"><ChevronRight size={13} />Data is fetched from configured endpoints; unavailable subsystems remain visibly unconfigured.</div>
      <div className="flex flex-wrap gap-3 text-xs">{['/overview', '/data-health', '/models', '/knowledge-base', '/forecast-operations', '/scenario-engine'].map((href) => <Link key={href} href={href} className="text-admin-neon-green hover:underline">{href.slice(1)}</Link>)}</div>
    </div>
  );
}

function DataPanel({ title, value, query, setQuery }: { title: string; value: Json | string; query: string; setQuery: (value: string) => void }) {
  const [open, setOpen] = useState(true);
  if (typeof value === 'string') return <section className="admin-card p-5 border-amber-500/20"><h2 className="font-mono text-xs text-admin-amber mb-2">{title}</h2><p className="text-sm text-admin-text-secondary">{value}</p></section>;
  const arrays = Object.entries(value).filter(([, item]) => Array.isArray(item));
  const scalar = Object.entries(value).filter(([, item]) => !Array.isArray(item) && (item === null || typeof item !== 'object'));
  const filter = (row: Json) => !query || JSON.stringify(row).toLowerCase().includes(query.toLowerCase());
  return <section className="admin-card p-5"><div className="flex flex-wrap items-center justify-between gap-2 mb-3"><h2 className="font-mono text-xs text-admin-neon-green break-all">{title}</h2><div className="flex gap-2"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter results" className="w-40 rounded border border-admin-border bg-admin-bg px-2 py-1 text-xs" /><button onClick={() => setOpen(!open)} className="admin-btn-secondary text-xs">{open ? 'Collapse' : 'Expand'}</button></div></div>
    {open && <>
      {scalar.length > 0 && <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 mb-4">{scalar.map(([key, item]) => <div key={key} className="rounded-lg bg-admin-bg-secondary/50 p-3"><p className="font-mono text-[10px] uppercase text-admin-text-muted">{key.replaceAll('_', ' ')}</p><p className="mt-1 text-sm break-all">{displayValue(item)}</p></div>)}</div>}
      {arrays.map(([key, rows]) => { const items = (rows as Json[]).filter((row) => typeof row === 'object' && row !== null && filter(row)); const cols = Array.from(new Set(items.flatMap((row) => Object.keys(row)))).slice(0, 12); return <div key={key} className="mb-4 last:mb-0"><div className="flex justify-between text-xs text-admin-text-muted mb-2"><span className="uppercase font-mono">{key.replaceAll('_', ' ')}</span><span>{items.length} records</span></div>{items.length === 0 ? <p className="py-4 text-center text-xs text-admin-text-muted">No records</p> : <div className="overflow-auto max-h-[28rem]"><table className="w-full text-left text-xs"><thead className="sticky top-0 bg-admin-card"><tr>{cols.map((col) => <th key={col} className="p-2 border-b border-admin-border text-admin-text-muted font-mono">{col}</th>)}</tr></thead><tbody>{items.slice(0, 300).map((row, index) => <tr key={String(row.id ?? row.series_id ?? row.model_id ?? index)} className="border-b border-admin-border/50">{cols.map((col) => { const cell = row[col]; return <td key={col} className="p-2 align-top text-admin-text-secondary max-w-xs"><span className="line-clamp-3 break-words">{displayValue(cell)}</span>{typeof cell === 'object' && cell !== null && <details className="mt-1"><summary className="cursor-pointer text-admin-neon-green">inspect</summary><pre className="max-w-lg whitespace-pre-wrap">{pretty(cell)}</pre></details>}</td>; })}</tr>)}</tbody></table></div>}</div>; })}
      <details><summary className="cursor-pointer text-[11px] text-admin-text-muted">Raw API response</summary><pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-admin-bg p-3 text-[11px] text-admin-text-secondary">{pretty(value)}</pre></details>
    </>}
  </section>;
}
