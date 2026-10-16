'use client';

import { useEffect, useState } from 'react';
import { PageShell } from '@/components/layout';
import { getRegimes, type RegimeResponse } from '@/lib/advanced-api';

export function RegimeProbabilityWorkspace() {
  const [data, setData] = useState<RegimeResponse | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { let active = true; getRegimes().then((value) => { if (active) setData(value); }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'Regime API unavailable'); }); return () => { active = false; }; }, []);
  const latest = data?.regimes.at(-1);
  const ready = Boolean(data?.regimes.length);
  return <PageShell title="Economic Regime Patterns" description="Historical output from the supplied two-state Gaussian HMM package.">
    <div className="space-y-5">
      <div className="rounded-xl border border-cyan-300/15 bg-cyan-400/[0.05] p-4 text-xs leading-5 text-cyan-50"><strong>{ready ? 'Connected supplied HMM artifact.' : 'Regime artifact unavailable.'}</strong> These are full-sample smoothed probabilities and use information from later dates. They are not real-time probabilities, causal regime labels, or policy signals.</div>
      {error && <p className="text-sm text-rose-300">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><p className="text-[10px] uppercase tracking-wider text-emerald-200">{data?.status.replaceAll('_', ' ') ?? 'Loading'}</p><h2 className="mt-3 text-xl font-semibold">{latest?.regime ?? 'Loading model output'}</h2><p className="mt-2 text-xs text-slate-400">{latest ? `Month ${latest.data_vintage} · smoothed state probability ${(latest.probability * 100).toFixed(1)}%` : 'Reading the checksum-verified supplied HMM artifact.'}</p></section>
        <section className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><h2 className="text-sm font-semibold">Model limits</h2><p className="mt-3 text-xs leading-5 text-slate-400">The supplied two-state model labels higher and lower inflation patterns. It does not separate supply shocks, demand pressure, or stagflation causes. Probabilities are smoothed over the full sample, so this is an ex-post descriptive diagnostic.</p></section>
      </div>
      <section className="rounded-xl border border-white/[0.08] bg-slate-900/60 p-5"><div className="flex items-center justify-between"><h2 className="text-sm font-semibold">Historical smoothed state probabilities</h2><span className="text-[10px] text-slate-500">{data?.regimes.length ?? 0} monthly records</span></div><div className="mt-4 max-h-[560px] overflow-auto"><table className="w-full min-w-[520px] text-left text-xs"><thead className="sticky top-0 bg-slate-900 text-[10px] uppercase text-slate-500"><tr><th className="py-2">Month</th><th className="py-2">Most likely pattern</th><th className="py-2">Posterior probability</th></tr></thead><tbody>{(data?.regimes.slice(-36).reverse() ?? []).map((item) => <tr key={item.data_vintage} className="border-t border-white/[0.06]"><td className="py-2 text-slate-400">{item.data_vintage}</td><td className="py-2 text-slate-200">{item.regime}</td><td className="py-2 text-slate-300">{(item.probability * 100).toFixed(1)}%</td></tr>)}</tbody></table></div></section>
      {data?.warnings.map((warning) => <p key={warning} className="text-xs leading-5 text-slate-500">{warning}</p>)}
    </div>
  </PageShell>;
}
