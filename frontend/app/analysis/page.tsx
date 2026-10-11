import { AlertTriangle, Info } from 'lucide-react';
import { ConfidenceMeter, InflationDecomposition, KPIGrid, MacroChart, SourceBadge } from '@/components';
import { PageShell } from '@/components/layout';
import { StatusState } from '@/components/ui';
import { mockCpiForecast, mockCpiHistoricalTimeSeries, mockInflationAnalysisKpis, mockInflationDecomposition, mockInflationDrivers, mockMacroObservations, mockModelIntegrationNote } from '@/lib/mock-data';

export default function AnalysisPage() {
	return <PageShell title="Inflation Analysis" description="Understand the headline inflation picture, its drivers, and the evidence behind current price pressures.">
		<div className="space-y-6">
			<div className="flex items-start gap-3 rounded-2xl border border-amber-300/15 bg-amber-400/[0.07] px-4 py-3 text-xs text-amber-100"><AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-300" /><span><strong>MOCK ANALYSIS</strong><span className="ml-2 text-amber-200/70">Values and interpretation are illustrative demo content.</span></span></div>
			<KPIGrid items={mockInflationAnalysisKpis} />
			<div className="grid gap-5 xl:grid-cols-[1.55fr_1fr]"><MacroChart observations={mockMacroObservations} historical={mockCpiHistoricalTimeSeries} forecast={mockCpiForecast} /><InflationDecomposition items={mockInflationDecomposition} /></div>
			<section className="rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.22)] backdrop-blur-2xl"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-300">Key inflation drivers</p><h2 className="mt-1 text-base font-semibold text-slate-50">What is driving the demo snapshot?</h2></div><div className="mt-4 grid gap-4 md:grid-cols-3">{mockInflationDrivers.map((driver) => <article key={driver.id} className="rounded-xl border border-white/[0.07] bg-white/[0.035] p-4"><div className="flex items-center justify-between gap-2"><h3 className="text-sm font-semibold text-slate-100">{driver.title}</h3><SourceBadge source={driver.sourceLabel} /></div><p className="mt-2 text-xs leading-5 text-slate-400">{driver.summary}</p><p className="mt-3 text-sm font-semibold text-slate-50">{driver.observation.value} {driver.observation.unit}</p><p className="mt-1 text-[10px] text-slate-500">Observed {driver.observation.date}</p><div className="mt-3"><ConfidenceMeter value={driver.observation.confidence * 100} /></div></article>)}</div></section>
			<StatusState kind="unavailable-model" title={mockModelIntegrationNote.title} message={mockModelIntegrationNote.text} />
			<div className="rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.22)] backdrop-blur-2xl"><div className="flex items-center gap-2"><Info size={16} className="text-cyan-300" /><h2 className="text-base font-semibold text-slate-50">Evidence & Sources</h2></div><div className="mt-4 flex flex-wrap gap-2">{mockInflationDrivers.map((driver) => <SourceBadge key={driver.id} source={driver.observation.source} href={driver.observation.sourceUrl} date={driver.observation.date} seriesId={driver.observation.id} confidence={driver.observation.confidence} status={driver.observation.status} showMetadata />)}</div></div>
		</div>
	</PageShell>;
}
