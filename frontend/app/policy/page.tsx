'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { PageShell } from '@/components/layout';
import { getApiHealth, getProjectSeriesCatalog, type ApiHealth, type ProjectSeriesCatalogItem } from '@/lib/research-api';

export default function PolicyPage() {
  const [series, setSeries] = useState<ProjectSeriesCatalogItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<ApiHealth | null>(null);
  useEffect(() => {
    Promise.all([getProjectSeriesCatalog(), getApiHealth()])
      .then(([catalog, status]) => { setSeries(catalog); setHealth(status); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'API unavailable'));
  }, []);
  const available = series.filter((item) => item.available);
  return <PageShell title="Policy Research" description="Review live observed indicators, model-package status, and the evidence available for policy analysis.">
    <div className="space-y-5"><div className="flex gap-3 rounded-xl border border-amber-300/20 bg-amber-400/[0.06] p-4 text-xs leading-5 text-amber-100"><AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-300"/><span><strong>No policy optimizer is connected.</strong> Static recommendations and scorecards have been removed. The project has datasets and forecasts, but no validated policy-loss function or calibrated transmission model to rank rate choices.</span></div>
      {health && <section className="grid gap-3 sm:grid-cols-3"><Status label="API" value={health.status === 'ok' ? 'Connected' : health.status} /><Status label="LLM" value={health.llm === 'configured' ? 'Configured' : 'Not configured'} /><Status label="Forecast package" value={health.final_model_package === 'configured' ? 'Configured' : 'Not configured'} /></section>}
      {error && <p className="text-sm text-rose-300">Could not load API data: {error}</p>}
      <section className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><h2 className="text-base font-semibold">Evidence available to analysts</h2><p className="mt-1 text-xs text-slate-400">Current series coverage from the API; availability does not imply a causal policy relationship.</p><div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{available.map((item) => <article key={item.id} className="rounded-lg border border-white/[0.07] p-4"><h3 className="text-sm font-semibold">{item.id.replaceAll('_', ' ')}</h3><p className="mt-2 text-xs text-slate-400">Latest: {item.latest?.value ?? '—'} {item.unit}</p><p className="mt-1 text-[10px] text-slate-500">{item.latest?.date ?? '—'} · {item.observation_count} observations · {item.source}</p></article>)}</div>{!available.length && !error && <p className="mt-4 text-sm text-slate-400">No observed series are available from the API.</p>}</section>
      <section className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><h2 className="text-base font-semibold">Evidence boundary</h2><p className="mt-2 text-xs leading-5 text-slate-400">The live series and CPI forecast package are connected above. A policy recommendation requires a calibrated monetary-transmission model, explicit loss function, counterfactual validation, and uncertainty assessment; those artifacts are not present in the supplied package, so this page does not invent a rate recommendation.</p></section>
    </div>
  </PageShell>;
}

function Status({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-emerald-300/15 bg-emerald-400/[0.05] p-4"><p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-2 text-sm font-semibold text-emerald-200">{value}</p></div>;
}
