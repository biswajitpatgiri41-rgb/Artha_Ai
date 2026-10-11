'use client';

import { HelpCircle } from 'lucide-react';
import type { PageAssistantContext } from '@/lib/assistant-context';

export interface AskWhyChartContext {
  chartId: string;
  selectedSeries: string;
  visibleDateRange?: { start?: string; end?: string };
  selectedPoint?: { date: string; value?: number };
  modelVersion?: string;
  sourceMetadata?: string;
  mode?: 'mock' | 'live' | 'none';
}

export function AskWhyButton({ chart }: { chart: AskWhyChartContext }) {
  const ask = () => {
    const page = window.location.pathname;
    const pageData: PageAssistantContext = {
      page, mode: chart.mode ?? 'none',
      visibleMetrics: chart.selectedPoint ? [{ label: `Selected point · ${chart.chartId}`, value: `${chart.selectedPoint.date}${chart.selectedPoint.value == null ? '' : ` · ${chart.selectedPoint.value}`}`, source: chart.sourceMetadata ?? 'Not available' }] : [],
      selectedScenario: null,
      selectedSeries: {
        chart_identity: chart.chartId, series: chart.selectedSeries,
        visible_date_range: `${chart.visibleDateRange?.start ?? 'not recorded'} to ${chart.visibleDateRange?.end ?? 'not recorded'}`,
        selected_point: chart.selectedPoint ? `${chart.selectedPoint.date}${chart.selectedPoint.value == null ? '' : `=${chart.selectedPoint.value}`}` : null,
        model_version: chart.modelVersion ?? null,
        source_metadata: chart.sourceMetadata ?? null,
      },
      warnings: chart.mode === 'mock' ? ['Chart contains mock/demo data; do not treat it as a current official observation.'] : [],
    };
    window.dispatchEvent(new CustomEvent('assistant:ask-why', { detail: { chartId: chart.chartId, pageData } }));
  };
  return <button type="button" onClick={ask} className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-300/15 bg-cyan-300/[0.04] px-2.5 py-1.5 text-[10px] font-semibold text-cyan-100 transition hover:bg-cyan-300/[0.08]" aria-label={`Ask Why about ${chart.chartId}`}><HelpCircle size={13} />Ask Why?</button>;
}
