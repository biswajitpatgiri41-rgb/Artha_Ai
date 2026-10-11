import { AlertTriangle, CheckCircle2, CircleDashed } from 'lucide-react';
import { AgentTimeline } from '@/components';
import { PageShell } from '@/components/layout';
import { StatusState } from '@/components/ui';
import { mockAgentExecutionEvents, MOCK_DATA_NOTICE } from '@/lib/mock-data';

export default function LogsPage() {
	const completed = mockAgentExecutionEvents.filter((event) => event.status === 'completed').length;
	const warnings = mockAgentExecutionEvents.filter((event) => event.status === 'warning').length;
	const pending = mockAgentExecutionEvents.filter((event) => event.status === 'pending' || event.status === 'queued').length;

	return (
		<PageShell title="Agent Logs" description="Observe the future research workflow trace using static mock events. No agents, LLM, or streaming backend is connected.">
			<div className="space-y-6">
				<div className="flex items-start gap-3 rounded-2xl border border-amber-300/15 bg-amber-400/[0.07] px-4 py-3 text-xs text-amber-100"><AlertTriangle size={17} className="mt-0.5 shrink-0 text-amber-300" /><span><strong>MOCK AGENT EVENTS</strong><span className="ml-2 text-amber-200/70">{MOCK_DATA_NOTICE} Metadata only; no chain-of-thought or hidden reasoning is displayed.</span></span></div>
				<div className="max-w-xl"><StatusState kind="unavailable-agent" compact /></div>
				<div className="grid gap-4 sm:grid-cols-3"><div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-emerald-700"><CheckCircle2 size={16} /><span className="text-[10px] font-semibold uppercase tracking-[0.12em]">Completed</span></div><p className="mt-3 text-2xl font-semibold text-slate-900">{completed}</p></div><div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-amber-700"><AlertTriangle size={16} /><span className="text-[10px] font-semibold uppercase tracking-[0.12em]">Warnings</span></div><p className="mt-3 text-2xl font-semibold text-slate-900">{warnings}</p></div><div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-slate-500"><CircleDashed size={16} /><span className="text-[10px] font-semibold uppercase tracking-[0.12em]">Pending stages</span></div><p className="mt-3 text-2xl font-semibold text-slate-900">{pending}</p></div></div>
				<section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40"><div className="mb-5 flex items-end justify-between gap-4"><div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-700">Execution order</p><h2 className="mt-1 text-lg font-semibold text-slate-950">Research run trace</h2></div><span className="text-[10px] uppercase tracking-[0.1em] text-slate-400">{mockAgentExecutionEvents.length} mock events</span></div><AgentTimeline events={mockAgentExecutionEvents} /></section>
			</div>
		</PageShell>
	);
}
