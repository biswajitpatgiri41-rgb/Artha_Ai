import type { MockStatus } from '@/lib/types';

interface SourceBadgeProps {
	source: string;
	href?: string;
	date?: string;
	retrievedDate?: string;
	seriesId?: string;
	confidence?: number;
	status?: MockStatus;
	showMetadata?: boolean;
}

export function SourceBadge({ source, href, date, retrievedDate, seriesId, confidence, status = 'mock', showMetadata = false }: SourceBadgeProps) {
	const statusClass = status === 'error' ? 'bg-red-50 text-red-700 ring-red-200' : status === 'warning' ? 'bg-amber-50 text-amber-700 ring-amber-200' : status === 'validated' ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-slate-100 text-slate-600 ring-slate-200';
	const label = <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold ring-1 ring-inset ${statusClass}`}><span className={`h-1.5 w-1.5 rounded-full ${status === 'error' ? 'bg-red-500' : status === 'warning' ? 'bg-amber-500' : status === 'validated' ? 'bg-emerald-500' : 'bg-slate-400'}`} />{source}{status === 'mock' && <span className="font-normal opacity-70">· mock</span>}</span>;

	return (
		<span className="inline-flex max-w-full flex-col items-start gap-1">
			{href ? <a href={href} target="_blank" rel="noreferrer" className="hover:opacity-80">{label}</a> : label}
			{showMetadata && <span className="text-[10px] leading-4 text-slate-400">{seriesId && `ID ${seriesId} · `}{date && `Observed ${date} · `}{retrievedDate && `Retrieved ${retrievedDate}`}{confidence !== undefined && ` · ${Math.round(confidence * 100)}% confidence`}</span>}
		</span>
	);
}
