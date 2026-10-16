'use client';

import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Radio } from 'lucide-react';
import type { EventCategory, OperationalEvent } from './demo-event-engine';

const filters: Array<'all' | EventCategory> = ['all', 'agents', 'data', 'tools', 'errors'];
const dotStyles: Record<EventCategory, string> = { data: 'bg-cyan-300', agents: 'bg-indigo-300', tools: 'bg-amber-300', policy: 'bg-violet-300', errors: 'bg-rose-300' };

export function EventStream({ events, running }: { events: OperationalEvent[]; running: boolean }) {
  const [collapsed, setCollapsed] = useState(false);
  const [filter, setFilter] = useState<'all' | EventCategory>('all');
  const bottomRef = useRef<HTMLDivElement>(null);
  const visibleEvents = events.filter((event) => filter === 'all' || event.type === filter);
  useEffect(() => { if (running) bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [events, running]);
  if (collapsed) return <button type="button" onClick={() => setCollapsed(false)} className="flex h-full min-h-[140px] items-start justify-center rounded-xl border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-2 text-slate-400 backdrop-blur-2xl" aria-label="Expand live event stream"><ChevronRight size={15} /><span className="writing-mode-vertical ml-1 text-[9px] font-semibold uppercase tracking-[0.14em]">Live Events</span></button>;
  return <section className="flex h-[660px] min-h-0 flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-[rgba(15,23,42,0.62)] shadow-[0_16px_40px_rgba(0,0,0,0.18)] backdrop-blur-2xl"><div className="flex items-center justify-between border-b border-white/[0.08] px-3 py-2.5"><div className="flex items-center gap-2"><Radio size={13} className={running ? 'text-cyan-300' : 'text-slate-500'} /><h2 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-200">Runtime Events</h2></div><button type="button" onClick={() => setCollapsed(true)} aria-label="Collapse runtime event stream" className="rounded-md p-1 text-slate-500 hover:bg-white/10 hover:text-white"><ChevronDown size={15} /></button></div><div className="flex flex-wrap gap-1 border-b border-white/[0.08] p-2">{filters.map((item) => <button key={item} type="button" onClick={() => setFilter(item)} className={`rounded-md px-1.5 py-1 text-[8px] font-semibold uppercase tracking-[0.08em] transition ${filter === item ? 'bg-cyan-400/10 text-cyan-200' : 'text-slate-500 hover:bg-white/[0.04] hover:text-slate-300'}`}>{item}</button>)}</div><div className="min-h-0 flex-1 overflow-y-auto p-2">{visibleEvents.length === 0 ? <p className="p-2 text-[11px] text-slate-500">Select Run Flow to inspect the connected runtime path.</p> : <div className="space-y-1.5">{visibleEvents.map((event) => <article key={event.id} className="rounded-lg border border-white/[0.05] bg-white/[0.025] p-2"><div className="flex items-center gap-1.5 text-[8px] text-slate-500"><span className={`h-1.5 w-1.5 rounded-full ${dotStyles[event.type]}`} />{event.timestamp}<span className="text-slate-600">·</span><span className="font-semibold uppercase tracking-[0.06em] text-slate-400">{event.node}</span></div><p className="mt-1 text-[10px] leading-4 text-slate-300">{event.message}</p>{event.duration && <p className="mt-0.5 text-[8px] text-slate-500">{event.duration}</p>}</article>)}<div ref={bottomRef} /></div>}</div><div className="border-t border-white/[0.08] px-3 py-1.5 text-[8px] uppercase tracking-[0.1em] text-slate-600">Connected runtime path · evidence events</div></section>;
}
