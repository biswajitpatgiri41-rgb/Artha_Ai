'use client';

import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle, FileText, Info, Loader2, Search, Table, Trash2, Upload, X } from 'lucide-react';

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
const RUN_ID_KEY = 'india-monetary-policy-evidence-run-id';
const SELECTED_KEY = 'india-monetary-policy-evidence-selected';
const ACCEPTED = ['.pdf', '.csv', '.xlsx', '.json', '.txt', '.md'];

interface EvidenceFile {
  evidence_id: string; run_id: string; original_filename: string; stored_filename: string;
  mime_type: string; size: number; uploaded_at: string; format: string; status: string;
  lifecycle: 'temporary' | 'saved';
  page_count?: number; chunk_count?: number; indexed_chunk_count?: number; error_message?: string;
  parser_warnings: string[]; row_count?: number; columns?: string[]; sheet_names?: string[];
  data_types?: Record<string, string>; top_level_keys?: string[]; json_schema?: unknown;
}
interface SearchResult { evidence_id: string; filename: string; format: string; location: { page?: number; section?: string; chunk_id?: string; rows?: number[]; columns?: string[]; sheet?: string; path?: string; keys?: string[] }; excerpt?: string; structured_result?: unknown; retrieval_score?: number; run_id: string; }
interface SearchResponse { results: SearchResult[]; warnings: string[]; }
interface RuntimeConfig {
  max_upload_bytes: number; max_upload_mb: number; max_files_per_run: number;
  max_pdf_pages: number; max_csv_rows: number; max_xlsx_sheets: number;
  max_json_bytes: number; evidence_retention_hours: number; privacy_notice: string;
}

function displaySize(bytes: number): string { return bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1048576).toFixed(1)} MB`; }
function locationLabel(location: SearchResult['location']): string {
  if (location.page) return `Page ${location.page}`;
  if (location.sheet) return `${location.sheet}${location.rows?.length ? ` Â· rows ${location.rows.join(', ')}` : ''}`;
  if (location.path) return `JSON path: ${location.path}`;
  return location.section ?? 'Document excerpt';
}
function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = { uploading: 'text-cyan-200 bg-cyan-400/10', parsing: 'text-blue-200 bg-blue-400/10', indexing: 'text-teal-200 bg-teal-400/10', ready: 'text-emerald-200 bg-emerald-400/10', failed: 'text-rose-200 bg-rose-400/10' };
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${styles[status] ?? 'text-slate-300 bg-white/10'}`}>{['uploading', 'parsing', 'indexing'].includes(status) && <Loader2 size={11} className="animate-spin" />}{status}</span>;
}

export default function EvidencePage() {
  const [runId, setRunId] = useState('');
  const [files, setFiles] = useState<EvidenceFile[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [metadataFile, setMetadataFile] = useState<EvidenceFile | null>(null);
  const [maxBytes, setMaxBytes] = useState(50 * 1048576);
  const [privacyNotice, setPrivacyNotice] = useState('');
  const [limits, setLimits] = useState<RuntimeConfig | null>(null);
  const [lifecycle, setLifecycle] = useState<'temporary' | 'saved'>('temporary');
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [busy, setBusy] = useState<'loading' | 'uploading' | 'searching' | null>('loading');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      let id = window.sessionStorage.getItem(RUN_ID_KEY);
      if (!id) { id = window.crypto.randomUUID(); window.sessionStorage.setItem(RUN_ID_KEY, id); }
      setRunId(id);
      try { setSelectedIds(JSON.parse(window.sessionStorage.getItem(SELECTED_KEY) ?? '[]') as string[]); } catch { setSelectedIds([]); }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const loadFiles = useCallback(async (activeRunId: string) => {
    const response = await fetch(`${apiBaseUrl}/evidence/run/${encodeURIComponent(activeRunId)}`, { cache: 'no-store' });
    const payload = await response.json();
    if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : `Could not load evidence (HTTP ${response.status}).`);
    const nextFiles = (payload.evidence ?? []) as EvidenceFile[];
    setFiles(nextFiles);
    const available = new Set(nextFiles.map((file) => file.evidence_id));
    setSelectedIds((current) => {
      const next = current.filter((id) => available.has(id));
      try { window.sessionStorage.setItem(SELECTED_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  useEffect(() => {
    if (!runId) return;
    let active = true;
    const timer = window.setTimeout(() => {
      void Promise.all([
        loadFiles(runId).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'Could not load evidence.'); }),
        fetch(`${apiBaseUrl}/evidence/config`, { cache: 'no-store' }).then((response) => response.ok ? response.json() as Promise<RuntimeConfig> : null).then((config) => { if (active && config) { setLimits(config); setMaxBytes(config.max_upload_bytes); setPrivacyNotice(config.privacy_notice); } }).catch(() => undefined),
      ]).finally(() => { if (active) setBusy(null); });
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [runId, loadFiles]);

  useEffect(() => {
    if (!runId || !files.some((file) => ['uploading', 'parsing', 'indexing'].includes(file.status))) return;
    const timer = window.setInterval(() => { void loadFiles(runId).catch(() => undefined); }, 1200);
    return () => window.clearInterval(timer);
  }, [runId, files, loadFiles]);

  const chooseFile = (file: File | null) => {
    setError(null); setNotice(null);
    if (!file) { setSelectedFile(null); return; }
    const ext = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`;
    if (!ACCEPTED.includes(ext)) { setSelectedFile(null); setError('Unsupported format. Choose PDF, CSV, XLSX, JSON, TXT, or MD.'); return; }
    if (file.size > maxBytes) { setSelectedFile(null); setError(`File exceeds the configured ${displaySize(maxBytes)} limit.`); return; }
    if (file.size === 0) { setSelectedFile(null); setError('Empty files cannot be uploaded.'); return; }
    setSelectedFile(file);
  };

  const upload = async () => {
    if (!runId || !selectedFile) return;
    setError(null); setNotice(null); setBusy('uploading'); setUploadProgress(0);
    try {
      const body = new FormData(); body.append('run_id', runId); body.append('lifecycle', lifecycle); body.append('file', selectedFile);
      const payload = await new Promise<Record<string, unknown>>((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open('POST', `${apiBaseUrl}/evidence/upload`);
        request.upload.onprogress = (event) => { if (event.lengthComputable) setUploadProgress(Math.round((event.loaded / event.total) * 100)); };
        request.onerror = () => reject(new Error('Upload connection failed.'));
        request.onload = () => {
          let result: Record<string, unknown> = {};
          try { result = JSON.parse(request.responseText) as Record<string, unknown>; } catch { /* handled as an HTTP error below */ }
          if (request.status < 200 || request.status >= 300) reject(new Error(typeof result.detail === 'string' ? result.detail : `Upload failed (HTTP ${request.status}).`));
          else resolve(result);
        };
        request.send(body);
      });
      setSelectedFile(null); if (inputRef.current) inputRef.current.value = '';
      setNotice(`${String(payload.filename ?? selectedFile.name)} uploaded. Parsing and indexing status will update below.`);
      await loadFiles(runId);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Upload failed.'); }
    finally { setBusy(null); setUploadProgress(null); }
  };

  const remove = async (file: EvidenceFile) => {
    setError(null); setNotice(null);
    try {
      const response = await fetch(`${apiBaseUrl}/evidence/${encodeURIComponent(file.evidence_id)}?run_id=${encodeURIComponent(runId)}`, { method: 'DELETE' });
      const payload = await response.json();
      if (!response.ok) throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Could not remove evidence.');
      const next = selectedIds.filter((id) => id !== file.evidence_id); setSelectedIds(next); window.sessionStorage.setItem(SELECTED_KEY, JSON.stringify(next));
      if (metadataFile?.evidence_id === file.evidence_id) setMetadataFile(null);
      await loadFiles(runId);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not remove evidence.'); }
  };

  const toggleSelection = (evidenceId: string) => {
    const next = selectedIds.includes(evidenceId) ? selectedIds.filter((id) => id !== evidenceId) : [...selectedIds, evidenceId];
    setSelectedIds(next); window.sessionStorage.setItem(SELECTED_KEY, JSON.stringify(next));
  };

  const search = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!runId || !query.trim()) return;
    setError(null); setNotice(null); setBusy('searching');
    try {
      const response = await fetch(`${apiBaseUrl}/evidence/search`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ run_id: runId, query: query.trim(), top_k: 8 }) });
      const payload = await response.json() as SearchResponse | { detail?: string };
      if (!response.ok) throw new Error(typeof (payload as { detail?: unknown }).detail === 'string' ? (payload as { detail: string }).detail : 'Evidence search failed.');
      const result = payload as SearchResponse; setResults(result.results ?? []); setWarnings(result.warnings ?? []);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Evidence search failed.'); }
    finally { setBusy(null); }
  };

  const viewMetadata = async (file: EvidenceFile) => {
    try {
      const response = await fetch(`${apiBaseUrl}/evidence/${encodeURIComponent(file.evidence_id)}?run_id=${encodeURIComponent(runId)}`, { cache: 'no-store' });
      const payload = await response.json(); if (!response.ok) throw new Error(payload.detail ?? 'Metadata unavailable.');
      setMetadataFile(payload as EvidenceFile);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Metadata unavailable.'); }
  };

  return <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
    <header><p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-300">Research workspace</p><h1 className="mt-2 text-2xl font-semibold text-slate-50">Evidence Workspace</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">Upload run scoped sources for document citations and deterministic table lookups. Documents support narrative claims; they do not prove future forecast values.</p></header>
    {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-200"><AlertCircle size={17} className="mt-0.5 shrink-0" />{error}</div>}
    {notice && <div role="status" className="flex items-start gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-3 text-sm text-emerald-200"><CheckCircle size={17} className="mt-0.5 shrink-0" />{notice}</div>}
    <section className="rounded-2xl border border-teal-300/15 bg-slate-900/70 p-5 shadow-[0_0_28px_rgba(45,212,191,0.04)]">
      <div className="flex items-center gap-2"><Upload size={17} className="text-teal-300" /><h2 className="text-base font-semibold text-slate-100">Upload supporting evidence</h2></div>
      <p className="mt-1 text-xs text-slate-400">Accepted formats: PDF Â· CSV Â· XLSX Â· JSON Â· TXT Â· MD Â· Maximum configured size: {displaySize(maxBytes)} · Up to {limits?.max_files_per_run ?? '…'} files per run</p>
      {limits && <p className="mt-1 text-[11px] text-slate-500">Parser caps: PDF {limits.max_pdf_pages} pages · CSV/XLSX {limits.max_csv_rows.toLocaleString()} rows · XLSX {limits.max_xlsx_sheets} sheets · JSON {displaySize(limits.max_json_bytes)}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400"><label htmlFor="evidence-lifecycle">Keep uploaded evidence:</label><select id="evidence-lifecycle" value={lifecycle} onChange={(event) => setLifecycle(event.target.value as 'temporary' | 'saved')} className="rounded-lg border border-white/10 bg-slate-950/70 px-2.5 py-1.5 text-slate-200"><option value="temporary">Temporary (default)</option><option value="saved">Saved</option></select><span>{lifecycle === 'temporary' ? `Temporary files are removed after ${limits?.evidence_retention_hours ?? 24} hours.` : 'Saved files remain available in this local run storage until removed.'}</span></div>
      <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0] ?? null); }} className={`mt-4 rounded-xl border border-dashed p-6 text-center transition ${dragging ? 'border-teal-300 bg-teal-400/10' : 'border-white/15 bg-slate-950/40'}`}>
        <p className="text-sm text-slate-300">Drag and drop a document here</p><p className="my-2 text-xs text-slate-600">or</p>
        <button type="button" onClick={() => inputRef.current?.click()} className="rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-xs font-medium text-slate-200 hover:border-teal-300/30">Browse Files</button>
        <input ref={inputRef} type="file" accept={ACCEPTED.join(',')} aria-label="Browse evidence files" className="hidden" onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} />
        {selectedFile && <p className="mt-3 text-xs text-slate-400">{selectedFile.name} Â· {displaySize(selectedFile.size)}</p>}
        <button type="button" disabled={!selectedFile || !runId || busy !== null} onClick={() => void upload()} className="mt-3 rounded-lg bg-teal-400 px-4 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40">{busy === 'uploading' ? `Uploading ${uploadProgress ?? 0}%` : 'Upload file'}</button>
        {busy === 'uploading' && <div className="mx-auto mt-3 h-1.5 max-w-sm overflow-hidden rounded-full bg-white/10" role="progressbar" aria-label="Upload progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={uploadProgress ?? 0}><div className="h-full rounded-full bg-teal-300 transition-[width]" style={{ width: `${uploadProgress ?? 0}%` }} /></div>}
      </div>
      <p className="mt-3 flex gap-2 text-[11px] leading-5 text-slate-500"><Info size={14} className="mt-0.5 shrink-0" />{privacyNotice || 'Local development storage is scoped by run ID. Authentication and multi-user isolation are not implemented.'}</p>
    </section>

    <section className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-base font-semibold text-slate-100">Uploaded Evidence</h2><p className="mt-1 text-xs text-slate-400">{files.length} file{files.length === 1 ? '' : 's'} Â· selected evidence is optional in assistant context</p></div><button type="button" onClick={() => void loadFiles(runId)} disabled={!runId || busy !== null} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 disabled:opacity-50">Refresh status</button></div>
      {busy === 'loading' && <p className="mt-4 flex items-center gap-2 text-xs text-slate-400"><Loader2 size={14} className="animate-spin" />Loading evidenceâ€¦</p>}
      {files.length === 0 && busy !== 'loading' && <p className="mt-4 rounded-lg bg-white/[0.03] p-4 text-sm text-slate-400">No evidence has been uploaded for this run.</p>}
      {files.length > 0 && (
        <ul className="mt-3 divide-y divide-white/[0.07]">
          {files.map((file) => (
            <li key={file.evidence_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <span className="rounded-lg bg-teal-400/10 p-2 text-teal-200">
                  {['csv', 'xlsx', 'json'].includes(file.format) ? <Table size={17} /> : <FileText size={17} />}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">{file.original_filename}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {file.format.toUpperCase()} · {displaySize(file.size)} · {new Date(file.uploaded_at).toLocaleString()} · {file.lifecycle === 'saved' ? 'Saved' : 'Temporary'}
                    {file.indexed_chunk_count != null ? ` · ${file.indexed_chunk_count} indexed chunks` : ''}
                  </p>
                  {file.error_message && <p className="mt-1 text-xs text-rose-300">{file.error_message}</p>}
                  {file.parser_warnings?.map((warning) => <p key={warning} className="mt-1 text-xs text-amber-200">{warning}</p>)}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={file.status} />
                <button type="button" onClick={() => void viewMetadata(file)} className="rounded-md border border-white/10 px-2.5 py-1.5 text-[10px] text-slate-300 hover:bg-white/5">View metadata</button>
                <button type="button" onClick={() => void remove(file)} aria-label={`Remove ${file.original_filename}`} className="rounded-md border border-rose-300/10 p-1.5 text-rose-300 hover:bg-rose-300/10"><Trash2 size={14} /></button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>

    <section className="rounded-2xl border border-teal-300/10 bg-slate-900/70 p-5"><h2 className="text-base font-semibold text-slate-100">Use in current research run</h2><p className="mt-1 text-xs text-slate-400">Choose documents explicitly. New uploads are not attached automatically.</p>{files.length === 0 ? <p className="mt-3 text-xs text-slate-500">Upload evidence to select it for the assistant.</p> : <div className="mt-3 flex flex-wrap gap-2">{files.map((file) => <label key={file.evidence_id} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs ${selectedIds.includes(file.evidence_id) ? 'border-teal-300/30 bg-teal-300/[0.07] text-teal-100' : 'border-white/10 bg-white/[0.025] text-slate-400'} ${file.status !== 'ready' ? 'opacity-50' : ''}`}><input type="checkbox" disabled={file.status !== 'ready'} checked={selectedIds.includes(file.evidence_id)} onChange={() => toggleSelection(file.evidence_id)} className="accent-teal-400" />{file.original_filename}</label>)}</div>}</section>

    <section className="rounded-2xl border border-teal-300/10 bg-slate-900/70 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-teal-300">Evidence intelligence</p><h2 className="mt-1 text-base font-semibold text-slate-100">Official Policy Document Library</h2></div><span className="rounded-full border border-amber-300/20 px-2 py-1 text-[10px] font-semibold text-amber-200">LIBRARY INGESTION PENDING</span></div><p className="mt-2 text-xs leading-5 text-slate-400">RBI Monetary Policy Statements, MPC Resolutions, RBI Bulletins, MoSPI Releases, and economic reports will be added through a verified source ingestion workflow. No official documents are silently preloaded.</p><div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{['Publisher', 'Document title', 'Publication date', 'Source URL', 'Document version', 'Checksum'].map((field) => <div key={field} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-xs text-slate-400">{field}<p className="mt-1 text-slate-600">Provided with verified library record</p></div>)}</div><p className="mt-3 text-[11px] text-slate-500">Economic Knowledge Graph is a separate future module; no unsupported relationship claims are generated here.</p></section>

    <section className="rounded-2xl border border-white/10 bg-slate-900/70 p-5"><h2 className="text-base font-semibold text-slate-100">Evidence Timeline</h2><div className="mt-3 space-y-2">{files.slice().sort((a, b) => a.uploaded_at.localeCompare(b.uploaded_at)).map((file) => <div key={file.evidence_id} className="flex flex-wrap items-center justify-between gap-2 border-l border-teal-300/20 pl-3 text-xs"><span className="text-slate-300">{file.original_filename} · {file.status.toUpperCase()}</span><time className="text-slate-500">{new Date(file.uploaded_at).toLocaleString()}</time></div>)}{files.length === 0 && <p className="text-xs text-slate-500">No evidence events for this run.</p>}</div></section>

    <section className="rounded-2xl border border-white/10 bg-slate-900/70 p-5"><h2 className="text-base font-semibold text-slate-100">Evidence Search</h2><form onSubmit={(event) => void search(event)} className="mt-3 flex flex-col gap-3 sm:flex-row"><label className="sr-only" htmlFor="evidence-query">Search uploaded evidence</label><input id="evidence-query" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={2000} placeholder="Search document passages or structured evidenceâ€¦" className="min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2.5 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-teal-300/40" /><button type="submit" disabled={!runId || !query.trim() || busy !== null} className="inline-flex items-center justify-center gap-2 rounded-lg border border-teal-300/20 bg-teal-400/10 px-4 py-2.5 text-sm font-semibold text-teal-100 disabled:opacity-50"><Search size={16} />{busy === 'searching' ? 'Searchingâ€¦' : 'Search'}</button></form>
      <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-400">Retrieved Evidence Preview</h3>{warnings.map((warning) => <p key={warning} className="mt-2 text-xs text-amber-200">{warning}</p>)}{results.length > 0 ? <div className="mt-3 space-y-3">{results.map((item, index) => <article key={`${item.evidence_id}-${item.location.chunk_id ?? index}`} className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold text-slate-200">{item.filename}</p><span className="text-[11px] text-slate-500">{locationLabel(item.location)}{item.retrieval_score != null ? ` Â· score ${item.retrieval_score.toFixed(3)}` : ''}</span></div>{item.excerpt && <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">{item.excerpt}</p>}{item.structured_result != null && <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-slate-950/70 p-3 text-xs text-slate-300">{JSON.stringify(item.structured_result, null, 2)}</pre>}</article>)}</div> : warnings.length === 0 && <p className="mt-2 text-xs text-slate-500">Search will show excerpts with page, sheet, row, or JSON path citations when available.</p>}</section>
    <section className="rounded-2xl border border-white/10 bg-slate-900/70 p-5"><h2 className="text-base font-semibold text-slate-100">Current Run Evidence</h2><p className="mt-1 text-xs text-slate-400">Evidence references selected for optional assistant context. This does not change model forecasts.</p><div className="mt-3 flex flex-wrap gap-2">{files.filter((file) => selectedIds.includes(file.evidence_id)).map((file) => <span key={file.evidence_id} className="rounded-lg border border-teal-300/15 bg-teal-300/[0.05] px-3 py-2 text-xs text-teal-100">{file.original_filename} Â· {file.format.toUpperCase()}</span>)}{selectedIds.length === 0 && <p className="text-xs text-slate-500">No evidence selected.</p>}</div></section>

    {metadataFile && <div role="dialog" aria-modal="true" aria-label="Evidence metadata" className="fixed inset-0 z-[80] grid place-items-center bg-slate-950/70 p-4" onClick={() => setMetadataFile(null)}><section className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-2xl border border-teal-300/20 bg-[#08152a] p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}><div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-widest text-teal-300">Evidence metadata</p><h2 className="mt-1 text-base font-semibold text-slate-100">{metadataFile.original_filename}</h2></div><button type="button" onClick={() => setMetadataFile(null)} aria-label="Close metadata" className="rounded-lg p-2 text-slate-400 hover:bg-white/5"><X size={17} /></button></div><pre className="mt-4 overflow-auto rounded-xl bg-slate-950/70 p-4 text-xs leading-5 text-slate-300">{JSON.stringify({ ...metadataFile, stored_filename: '[server managed]' }, null, 2)}</pre></section></div>}
    <p className="text-[11px] leading-5 text-slate-500">Run ID: <code>{runId || 'Preparingâ€¦'}</code>. Files stay local to this run ID. This development app does not provide authentication or production multi-tenant isolation.</p>
  </main>;
}
