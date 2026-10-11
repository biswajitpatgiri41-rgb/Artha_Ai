import type { Kpi } from '@/lib/types';
import { Activity, ArrowDownRight, ArrowUpRight, Coins, DollarSign, Landmark, Minus, Wheat } from 'lucide-react';
import { SourceBadge } from './SourceBadge';

interface KPIGridProps {
	items: Kpi[];
}

export function KPIGrid({ items }: KPIGridProps) {
	const metricStyles: Record<string, { icon: typeof Activity; color: string; glow: string }> = {
		'Headline CPI': { icon: Activity, color: 'text-blue-300', glow: 'from-blue-500/60' },
		'Food Inflation': { icon: Wheat, color: 'text-emerald-300', glow: 'from-emerald-500/60' },
		'Repo Rate': { icon: Landmark, color: 'text-violet-300', glow: 'from-violet-500/60' },
		'GDP Growth': { icon: Activity, color: 'text-cyan-300', glow: 'from-cyan-400/60' },
		'INR/USD': { icon: DollarSign, color: 'text-amber-300', glow: 'from-amber-400/60' },
	};
	return (
		<section aria-label="Key performance indicators" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
			{items.map((item) => (
				<article key={item.label} className="group relative overflow-hidden rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.55)] p-4 shadow-[0_18px_45px_rgba(0,0,0,0.2)] backdrop-blur-2xl transition duration-200 hover:-translate-y-0.5 hover:border-blue-300/25 hover:shadow-[0_20px_45px_rgba(0,0,0,0.3),0_0_22px_rgba(59,130,246,0.1)]">
					<span className={`absolute inset-x-5 top-0 h-px bg-gradient-to-r ${metricStyles[item.label]?.glow ?? 'from-blue-500/40'} to-transparent`} />
					<div className="flex items-start justify-between gap-2">
						<div className="flex items-center gap-2">
							{(() => { const Icon = metricStyles[item.label]?.icon ?? Coins; return <Icon size={15} className={metricStyles[item.label]?.color ?? 'text-slate-300'} strokeWidth={1.8} />; })()}
							<p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-400">{item.label}</p>
						</div>
						{item.observation && <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" title="Mock observation available" />}
					</div>
					<div className="mt-4 flex items-end justify-between gap-2">
						<div>
							<p className="font-variant-numeric tabular-nums text-[2rem] font-semibold leading-none tracking-[-0.04em] text-slate-50">{item.value}</p>
							{item.observation && <p className="mt-2 text-[10px] text-slate-500">{item.observation.unit}</p>}
						</div>
						<span className={`inline-flex items-center gap-0.5 rounded-full border px-2 py-1 text-[10px] font-semibold ${item.trend === 'down' ? 'border-emerald-400/15 bg-emerald-400/10 text-emerald-300' : item.trend === 'up' ? 'border-cyan-400/15 bg-cyan-400/10 text-cyan-300' : 'border-white/[0.08] bg-white/[0.04] text-slate-400'}`}>
							{item.trend === 'down' ? <ArrowDownRight size={12} /> : item.trend === 'up' ? <ArrowUpRight size={12} /> : <Minus size={12} />}
							{item.change}
						</span>
					</div>
					{item.sparkline && item.sparkline.length > 1 && <Sparkline values={item.sparkline} color={metricStyles[item.label]?.color ?? 'text-blue-300'} />}
					<div className="mt-3 flex items-end justify-between gap-2 border-t border-white/[0.07] pt-3 text-[10px] text-slate-500">
						{item.observation ? <SourceBadge source={item.observation.source} href={item.observation.sourceUrl} date={item.observation.date} retrievedDate={item.observation.retrievedDate} seriesId={item.observation.id} confidence={item.observation.confidence} status={item.observation.status} showMetadata /> : <span>Demo summary · mock</span>}
					</div>
				</article>
			))}
		</section>
	);
}

function Sparkline({ values, color }: { values: number[]; color: string }) {
	const min = Math.min(...values);
	const range = Math.max(Math.max(...values) - min, 0.01);
	const points = values.map((value, index) => `${(index / (values.length - 1)) * 100},${28 - ((value - min) / range) * 22}`).join(' ');
	return <svg viewBox="0 0 100 30" className="mt-3 h-7 w-full overflow-visible opacity-80" aria-hidden="true"><polyline points={points} fill="none" className={color} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
