import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ArchitectureNode, ArchitectureCategory } from './architecture-model';
import { getNodeStatusLabel } from './demo-event-engine';

const categoryStyles: Record<ArchitectureCategory, { border: string; text: string; accent: string; glow: string }> = {
  source: { border: 'border-cyan-400/45', text: 'text-cyan-300', accent: 'bg-cyan-400', glow: 'shadow-[0_0_20px_rgba(34,211,238,0.10)]' },
  interface: { border: 'border-cyan-400/55', text: 'text-cyan-300', accent: 'bg-cyan-400', glow: 'shadow-[0_0_20px_rgba(34,211,238,0.10)]' },
  orchestration: { border: 'border-violet-400/55', text: 'text-violet-300', accent: 'bg-violet-400', glow: 'shadow-[0_0_20px_rgba(139,92,246,0.10)]' },
  agent: { border: 'border-blue-400/45', text: 'text-blue-300', accent: 'bg-blue-400', glow: 'shadow-[0_0_20px_rgba(59,130,246,0.10)]' },
  tool: { border: 'border-amber-300/45', text: 'text-amber-300', accent: 'bg-amber-300', glow: 'shadow-[0_0_20px_rgba(245,158,11,0.10)]' },
  model: { border: 'border-amber-300/55', text: 'text-amber-300', accent: 'bg-amber-300', glow: 'shadow-[0_0_20px_rgba(245,158,11,0.10)]' },
  explainability: { border: 'border-cyan-300/45', text: 'text-cyan-300', accent: 'bg-cyan-300', glow: 'shadow-[0_0_20px_rgba(34,211,238,0.10)]' },
  regime: { border: 'border-violet-400/45', text: 'text-violet-300', accent: 'bg-violet-400', glow: 'shadow-[0_0_20px_rgba(139,92,246,0.10)]' },
  policy: { border: 'border-violet-500/55', text: 'text-violet-300', accent: 'bg-violet-500', glow: 'shadow-[0_0_20px_rgba(124,58,237,0.10)]' },
  critic: { border: 'border-rose-400/55', text: 'text-rose-300', accent: 'bg-rose-400', glow: 'shadow-[0_0_20px_rgba(244,63,94,0.10)]' },
  report: { border: 'border-green-400/55', text: 'text-green-300', accent: 'bg-green-400', glow: 'shadow-[0_0_20px_rgba(34,197,94,0.10)]' },
  storage: { border: 'border-slate-400/35', text: 'text-slate-300', accent: 'bg-slate-400', glow: 'shadow-[0_0_20px_rgba(100,116,139,0.08)]' },
  evidence: { border: 'border-emerald-400/50', text: 'text-emerald-300', accent: 'bg-emerald-400', glow: 'shadow-[0_0_20px_rgba(52,211,153,0.10)]' },
  engineering: { border: 'border-blue-400/45', text: 'text-blue-300', accent: 'bg-blue-400', glow: 'shadow-[0_0_20px_rgba(59,130,246,0.10)]' },
  evaluation: { border: 'border-lime-300/45', text: 'text-lime-200', accent: 'bg-lime-300', glow: 'shadow-[0_0_20px_rgba(163,230,53,0.10)]' },
  scenario: { border: 'border-pink-400/45', text: 'text-pink-300', accent: 'bg-pink-400', glow: 'shadow-[0_0_20px_rgba(244,114,182,0.10)]' },
  output: { border: 'border-emerald-400/50', text: 'text-emerald-300', accent: 'bg-emerald-400', glow: 'shadow-[0_0_20px_rgba(52,211,153,0.10)]' },
};
const statusStyles = { idle: 'bg-slate-500', queued: 'bg-amber-400', running: 'bg-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.8)]', completed: 'bg-emerald-400', warning: 'bg-amber-400', failed: 'bg-rose-400' };

export function ArchitectureNode({ data }: NodeProps<ArchitectureNode>) {
  const Icon = data.icon; const style = categoryStyles[data.category]; const isRunning = data.status === 'running'; const isFailed = data.status === 'failed';
  const isUnavailable = data.category === 'source' || (data.category === 'model' && data.readiness !== 'connected');
  const statusLabel = data.readiness === 'connected' ? 'CONNECTED' : data.readiness === 'model_pending' ? 'MODEL INTEGRATION PENDING' : data.readiness === 'data_pending' ? 'DATA PENDING' : data.readiness === 'planned' ? 'PLANNED' : isUnavailable ? data.category === 'model' ? 'MODEL NOT CONNECTED' : 'NOT VERIFIED' : getNodeStatusLabel(data.status);
  const isSource = data.category === 'source';
  return <div className={`group relative cursor-pointer ${isSource ? 'min-h-[68px] w-[160px] p-3' : 'min-h-[96px] w-[185px] p-4'} rounded-2xl border bg-[rgba(8,15,30,0.88)] text-slate-100 backdrop-blur-xl transition-[box-shadow,border-color] duration-200 ${style.border} ${style.glow} hover:shadow-[0_0_20px_rgba(148,163,184,0.18)] ${data.selected ? 'border-white/45 shadow-[0_0_18px_rgba(148,163,184,0.16)]' : ''} ${isRunning ? 'animate-pulse shadow-[0_0_20px_rgba(148,163,184,0.28)]' : ''} ${isFailed ? 'border-rose-300/90 shadow-[0_0_20px_rgba(244,63,94,0.28)]' : ''}`}>
    <span className={`absolute inset-x-4 top-0 h-px ${style.accent} opacity-80`} />
    <Handle type="target" position={Position.Top} className="!h-1 !w-1 !border-0 !bg-slate-500/40 opacity-0 transition-opacity group-hover:opacity-100" />
    <div className="flex items-start justify-between gap-2" title={data.category === 'source' ? `${data.label}\nIndia macro and financial data\nStatus: Not verified` : undefined}><div className="flex min-w-0 items-center gap-2"><Icon size={18} strokeWidth={1.8} className={`shrink-0 ${style.text}`} /><p className="truncate text-[15px] font-semibold leading-5">{data.label}</p></div><span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${isUnavailable || data.readiness === 'planned' || data.readiness === 'model_pending' ? 'bg-slate-500' : data.readiness === 'connected' ? 'bg-emerald-400' : statusStyles[data.status]}`} title={statusLabel} /></div>
    {!isSource && <p className="mt-3 text-[11px] leading-4 text-slate-400">{data.description}</p>}
    <div className={`${isSource ? 'mt-2' : 'mt-3'} flex items-center ${isSource ? '' : 'border-t border-white/[0.08] pt-2'} text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500`}><span className={data.readiness === 'connected' || data.status === 'completed' ? 'text-emerald-300' : data.readiness === 'model_pending' ? 'text-amber-300' : data.readiness === 'planned' || data.readiness === 'data_pending' || isUnavailable ? 'text-slate-500' : isRunning ? 'text-cyan-300' : isFailed ? 'text-rose-300' : ''}>{isSource ? 'NOT VERIFIED' : statusLabel}</span></div>
    <Handle type="source" position={Position.Bottom} className="!h-1 !w-1 !border-0 !bg-slate-500/40 opacity-0 transition-opacity group-hover:opacity-100" />
  </div>;
}
