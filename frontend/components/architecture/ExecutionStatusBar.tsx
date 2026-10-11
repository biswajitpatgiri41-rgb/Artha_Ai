import { CheckCircle2, CircleDashed, LoaderCircle } from 'lucide-react';
import type { DemoFlowState } from './demo-event-engine';

export function ExecutionStatusBar({ state }: { state: DemoFlowState }) {
  const statuses = Object.values(state.nodeStatuses);
  const completed = statuses.filter((status) => status === 'completed').length;
  const running = statuses.filter((status) => status === 'running').length;
  const queued = statuses.filter((status) => status === 'queued').length;
  const failed = statuses.filter((status) => status === 'failed').length;
  const progress = Math.min(100, Math.round((completed / Math.max(state.totalSteps, 1)) * 100));
  const isComplete = state.phase === 'complete';
  return <section className="rounded-xl border border-white/[0.08] bg-[rgba(15,23,42,0.68)] px-4 py-3 shadow-[0_14px_35px_rgba(0,0,0,0.2)] backdrop-blur-xl"><div className="flex flex-wrap items-start justify-between gap-3"><div className="flex items-center gap-2"><span className={`grid h-6 w-6 place-items-center rounded-lg ${isComplete ? 'bg-emerald-400/10 text-emerald-300' : state.running ? 'bg-cyan-400/10 text-cyan-300' : 'bg-white/[0.05] text-slate-400'}`}>{isComplete ? <CheckCircle2 size={15} /> : state.running ? <LoaderCircle size={15} className="animate-spin" /> : <CircleDashed size={15} />}</span><div><p className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${isComplete ? 'text-emerald-300' : state.running ? 'text-cyan-300' : 'text-slate-300'}`}>{isComplete ? 'EXECUTION COMPLETE' : state.running ? `RUNNING · Step ${state.currentStep} / ${state.totalSteps}` : 'READY'}</p><p className="mt-0.5 text-[11px] text-slate-500">{isComplete ? 'Critic: PASSED · Report: GENERATED' : state.running ? `Current: ${state.currentNode || 'Preparing workflow'}` : 'Waiting for research request'}</p></div></div><span className="rounded-full border border-amber-300/15 bg-amber-400/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.12em] text-amber-200">DEMO SIMULATION</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.06]"><div className={`h-full rounded-full transition-all duration-500 ${isComplete ? 'bg-emerald-400' : 'bg-cyan-300'}`} style={{ width: `${progress}%` }} /></div><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-slate-500"><span>Nodes completed: {completed}</span><span>Running: {running}</span><span>Queued: {queued}</span><span>Failed: {failed}</span><span>Elapsed: {(state.elapsedMs / 1000).toFixed(1)}s</span></div></section>;
}
