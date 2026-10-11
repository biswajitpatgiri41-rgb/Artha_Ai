import type {
  AgentExecutionEvent,
  DataSource,
  EconomicObservation,
  ForecastPoint,
  InflationDecompositionItem,
  InflationDriver,
  Kpi,
  MacroObservation,
  MacroSignal,
  MacroSeries,
  NavigationItem,
  PolicyScorecardItem,
  PolicyAlternativeAnalysis,
  SavedReport,
  ScenarioResult,
  StaticAnalysisNote,
  TimeSeriesPoint,
} from './types';

export const MOCK_DATA_NOTICE = 'Mock demo data only. Values are illustrative and are not current official figures.';

export const navigationItems: NavigationItem[] = [
  { label: 'Overview', href: '/', status: 'ready' },
  { label: 'Analysis', href: '/analysis', status: 'planned' },
  { label: 'Forecasts', href: '/forecasts', status: 'planned' },
  { label: 'Simulator', href: '/simulator', status: 'planned' },
  { label: 'Policy', href: '/policy', status: 'planned' },
  { label: 'Data', href: '/data', status: 'planned' },
  { label: 'Evidence', href: '/evidence', status: 'ready' },
  { label: 'Logs', href: '/logs', status: 'planned' },
  { label: 'Reports', href: '/reports', status: 'planned' },
  { label: 'Architecture', href: '/architecture', status: 'ready' },
  { label: 'Regimes', href: '/regimes', status: 'planned' },
  { label: 'Data Quality', href: '/data-quality', status: 'planned' },
  { label: 'Model Registry', href: '/model-registry', status: 'planned' },
  { label: 'Knowledge Graph', href: '/knowledge-graph', status: 'planned' },
  { label: 'Agent Evaluation', href: '/agent-evaluation', status: 'planned' },
];

export const mockSources: DataSource[] = [
  { id: 'rbi-dbie', name: 'RBI DBIE', provider: 'Reserve Bank of India', url: 'https://data.rbi.org.in/', cadence: 'Monthly', coverage: 'Prices, rates, liquidity', status: 'mock', isMock: true },
  { id: 'mospi', name: 'MoSPI', provider: 'Ministry of Statistics and Programme Implementation', url: 'https://mospi.gov.in/', cadence: 'Monthly / quarterly', coverage: 'CPI and national accounts', status: 'mock', isMock: true },
  { id: 'world-bank', name: 'World Bank', provider: 'World Bank DataBank', url: 'https://data.worldbank.org/', cadence: 'Annual', coverage: 'Development indicators', status: 'mock', isMock: true },
  { id: 'imf', name: 'IMF', provider: 'International Monetary Fund', url: 'https://www.imf.org/en/Data', cadence: 'Quarterly / annual', coverage: 'Macro outlook', status: 'mock', isMock: true },
  { id: 'fred', name: 'FRED', provider: 'Federal Reserve Bank of St. Louis', url: 'https://fred.stlouisfed.org/', cadence: 'Daily / monthly', coverage: 'Global rates and markets', status: 'mock', isMock: true },
  { id: 'oecd', name: 'OECD', provider: 'Organisation for Economic Co-operation and Development', url: 'https://data.oecd.org/', cadence: 'Monthly / quarterly', coverage: 'Cross-country indicators', status: 'mock', isMock: true },
  { id: 'imd', name: 'IMD', provider: 'India Meteorological Department', url: 'https://mausam.imd.gov.in/', cadence: 'Seasonal', coverage: 'Monsoon and weather signals', status: 'mock', isMock: true },
  { id: 'eia', name: 'EIA', provider: 'U.S. Energy Information Administration', url: 'https://www.eia.gov/', cadence: 'Weekly / monthly', coverage: 'Energy and crude oil', status: 'mock', isMock: true },
];

const sourceUrl = (id: string) => mockSources.find((source) => source.id === id)?.url ?? '#';

const observation = (
  id: string,
  label: string,
  value: number,
  unit: string,
  date: string,
  source: string,
  confidence = 0.82,
): EconomicObservation => ({
  id,
  label,
  value,
  unit,
  date,
  source,
  sourceUrl: sourceUrl(source),
  retrievedDate: '2025-02-01',
  status: 'mock',
  confidence,
  isMock: true,
  note: MOCK_DATA_NOTICE,
});

export const mockCpiInflation = observation('cpi-headline-latest', 'CPI inflation', 4.8, '% year-on-year', '2025-01-01', 'mospi');
export const mockFoodInflation = observation('cpi-food-latest', 'Food inflation', 5.6, '% year-on-year', '2025-01-01', 'mospi', 0.76);
export const mockCoreInflation = observation('cpi-core-latest', 'Core inflation', 3.7, '% year-on-year', '2025-01-01', 'rbi-dbie', 0.74);
export const mockRepoRate = observation('repo-rate-latest', 'Repo rate', 6.5, '%', '2025-01-15', 'rbi-dbie', 0.9);
export const mockGdpGrowth = observation('gdp-growth-latest', 'Real GDP growth', 7.2, '% year-on-year', '2024-12-31', 'mospi');
export const mockInrUsd = observation('inr-usd-latest', 'INR / USD', 83.4, 'INR per USD', '2025-01-15', 'fred', 0.68);

export const mockSeriesCatalog: MacroSeries[] = [
  { id: 'india-cpi-headline', name: 'CPI', description: 'Consumer price index, headline inflation rate for India.', latestValue: mockCpiInflation.value, unit: '% year-on-year', frequency: 'Monthly', source: 'MoSPI', sourceUrl: sourceUrl('mospi'), baseYear: '2012 = 100', latestObservation: mockCpiInflation.date, status: 'mock', seasonalAdjustment: 'Not seasonally adjusted', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 4.9 }, { date: '2025-01-01', value: mockCpiInflation.value }], isMock: true },
  { id: 'india-food-cpi', name: 'Food CPI', description: 'Food and beverages component of consumer price inflation.', latestValue: mockFoodInflation.value, unit: '% year-on-year', frequency: 'Monthly', source: 'MoSPI', sourceUrl: sourceUrl('mospi'), baseYear: '2012 = 100', latestObservation: mockFoodInflation.date, status: 'mock', seasonalAdjustment: 'Not seasonally adjusted', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 5.8 }, { date: '2025-01-01', value: mockFoodInflation.value }], isMock: true },
  { id: 'india-gdp-growth', name: 'GDP', description: 'Real gross domestic product growth rate.', latestValue: mockGdpGrowth.value, unit: '% year-on-year', frequency: 'Quarterly', source: 'MoSPI', sourceUrl: sourceUrl('mospi'), baseYear: '2011-12 = 100', latestObservation: mockGdpGrowth.date, status: 'mock', seasonalAdjustment: 'Seasonally adjusted', retrievedDate: '2025-02-01', observations: [{ date: '2024-09-30', value: 7.4 }, { date: '2024-12-31', value: mockGdpGrowth.value }], isMock: true },
  { id: 'india-iip', name: 'IIP', description: 'Index of industrial production growth.', latestValue: 5.2, unit: '% year-on-year', frequency: 'Monthly', source: 'MoSPI', sourceUrl: sourceUrl('mospi'), baseYear: '2011-12 = 100', latestObservation: '2025-01-01', status: 'mock', seasonalAdjustment: 'Not seasonally adjusted', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 3.5 }, { date: '2025-01-01', value: 5.2 }], isMock: true },
  { id: 'india-repo-rate', name: 'Repo Rate', description: 'Policy repo rate set by the Reserve Bank of India.', latestValue: mockRepoRate.value, unit: '%', frequency: 'Daily', source: 'RBI DBIE', sourceUrl: sourceUrl('rbi-dbie'), baseYear: null, latestObservation: mockRepoRate.date, status: 'mock', seasonalAdjustment: 'Not applicable', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 6.5 }, { date: '2025-01-15', value: mockRepoRate.value }], isMock: true },
  { id: 'inr-usd', name: 'INR/USD', description: 'Illustrative Indian rupee exchange rate against the US dollar.', latestValue: mockInrUsd.value, unit: 'INR per USD', frequency: 'Daily', source: 'FRED', sourceUrl: sourceUrl('fred'), baseYear: null, latestObservation: mockInrUsd.date, status: 'mock', seasonalAdjustment: 'Not applicable', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 83.8 }, { date: '2025-01-15', value: mockInrUsd.value }], isMock: true },
  { id: 'india-credit-growth', name: 'Credit Growth', description: 'Non-food bank credit growth indicator.', latestValue: 15.1, unit: '% year-on-year', frequency: 'Monthly', source: 'RBI DBIE', sourceUrl: sourceUrl('rbi-dbie'), baseYear: null, latestObservation: '2025-01-01', status: 'mock', seasonalAdjustment: 'Not seasonally adjusted', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 14.2 }, { date: '2025-01-01', value: 15.1 }], isMock: true },
  { id: 'india-m3-growth', name: 'M3 Growth', description: 'Broad money growth indicator for India.', latestValue: 10.4, unit: '% year-on-year', frequency: 'Monthly', source: 'RBI DBIE', sourceUrl: sourceUrl('rbi-dbie'), baseYear: null, latestObservation: '2025-01-01', status: 'mock', seasonalAdjustment: 'Not seasonally adjusted', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 10.1 }, { date: '2025-01-01', value: 10.4 }], isMock: true },
  { id: 'brent-crude', name: 'Brent Crude', description: 'Illustrative Brent crude oil price.', latestValue: 78.4, unit: 'USD per barrel', frequency: 'Daily', source: 'EIA', sourceUrl: sourceUrl('eia'), baseYear: null, latestObservation: '2025-01-15', status: 'mock', seasonalAdjustment: 'Not applicable', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 74.5 }, { date: '2025-01-15', value: 78.4 }], isMock: true },
  { id: 'us-fed-rate', name: 'US Fed Rate', description: 'Illustrative upper bound of the US federal funds target range.', latestValue: 4.5, unit: '%', frequency: 'Daily', source: 'FRED', sourceUrl: sourceUrl('fred'), baseYear: null, latestObservation: '2025-01-15', status: 'mock', seasonalAdjustment: 'Not applicable', retrievedDate: '2025-02-01', observations: [{ date: '2024-10-01', value: 5.0 }, { date: '2025-01-15', value: 4.5 }], isMock: true },
  { id: 'rainfall-deviation', name: 'Rainfall Deviation', description: 'Monsoon rainfall deviation from the long-period average.', latestValue: -8.0, unit: '% from LPA', frequency: 'Seasonal', source: 'IMD', sourceUrl: sourceUrl('imd'), baseYear: '1991-2020 LPA', latestObservation: '2024-09-30', status: 'mock', seasonalAdjustment: 'Not applicable', retrievedDate: '2025-02-01', observations: [{ date: '2024-07-31', value: -5.0 }, { date: '2024-09-30', value: -8.0 }], isMock: true },
];

export const mockKpis: Kpi[] = [
  { label: 'Headline inflation', value: '4.8%', change: '-0.2 pp', trend: 'down', observation: mockCpiInflation },
  { label: 'Food inflation', value: '5.6%', change: '+0.3 pp', trend: 'up', observation: mockFoodInflation },
  { label: 'Repo rate', value: '6.50%', change: 'unchanged', trend: 'flat', observation: mockRepoRate },
  { label: 'Real GDP growth', value: '7.2%', change: '+0.4 pp', trend: 'up', observation: mockGdpGrowth },
  { label: 'Policy confidence', value: '78%', change: '+3 pts', trend: 'up' },
];

export const mockCpiHistoricalTimeSeries: TimeSeriesPoint[] = [
  { ...observation('cpi-2024-01', 'CPI inflation', 5.1, '% year-on-year', '2024-01-01', 'mospi'), period: 'Jan 24' },
  { ...observation('cpi-2024-04', 'CPI inflation', 4.8, '% year-on-year', '2024-04-01', 'mospi'), period: 'Apr 24' },
  { ...observation('cpi-2024-07', 'CPI inflation', 5.0, '% year-on-year', '2024-07-01', 'mospi'), period: 'Jul 24' },
  { ...observation('cpi-2024-10', 'CPI inflation', 4.9, '% year-on-year', '2024-10-01', 'mospi'), period: 'Oct 24' },
  { ...mockCpiInflation, id: 'cpi-2025-01', period: 'Jan 25' },
];

export const mockDashboardKpis: Kpi[] = [
  { label: 'Headline CPI', value: `${mockCpiInflation.value.toFixed(1)}%`, change: '↓ 0.2 pp', trend: 'down', observation: mockCpiInflation, sparkline: mockCpiHistoricalTimeSeries.map((point) => point.value) },
  { label: 'Food Inflation', value: `${mockFoodInflation.value.toFixed(1)}%`, change: '↑ 0.3 pp', trend: 'up', observation: mockFoodInflation },
  { label: 'Repo Rate', value: `${mockRepoRate.value.toFixed(2)}%`, change: '— unchanged', trend: 'flat', observation: mockRepoRate },
  { label: 'GDP Growth', value: `${mockGdpGrowth.value.toFixed(1)}%`, change: '↑ 0.4 pp', trend: 'up', observation: mockGdpGrowth, sparkline: [7.8, 7.6, 7.4, 7.3, mockGdpGrowth.value] },
  { label: 'INR/USD', value: mockInrUsd.value.toFixed(1), change: 'Demo baseline', trend: 'flat', observation: mockInrUsd },
];

export const mockCpiForecast: ForecastPoint[] = [
  { ...observation('cpi-2025-04', 'CPI forecast', 4.7, '% year-on-year', '2025-04-01', 'imf', 0.62), period: 'Apr 25', lowerBound: 4.0, upperBound: 5.4, isForecast: true },
  { ...observation('cpi-2025-07', 'CPI forecast', 4.5, '% year-on-year', '2025-07-01', 'imf', 0.58), period: 'Jul 25', lowerBound: 3.7, upperBound: 5.3, isForecast: true },
  { ...observation('cpi-2025-10', 'CPI forecast', 4.3, '% year-on-year', '2025-10-01', 'imf', 0.54), period: 'Oct 25', lowerBound: 3.4, upperBound: 5.2, isForecast: true },
  { ...observation('cpi-2026-01', 'CPI forecast', 4.2, '% year-on-year', '2026-01-01', 'imf', 0.5), period: 'Jan 26', lowerBound: 3.2, upperBound: 5.2, isForecast: true },
];

export const mockMacroObservations: MacroObservation[] = mockCpiHistoricalTimeSeries.map((point, index) => ({
  period: point.period,
  inflation: point.value,
  repoRate: index < 4 ? 6.5 : mockRepoRate.value,
  growth: [7.8, 7.6, 7.4, 7.3, mockGdpGrowth.value][index],
}));

export const mockInflationDecomposition: InflationDecompositionItem[] = [
  { category: 'Food and beverages', contribution: observation('decomp-food', 'Food contribution', 2.4, 'percentage points', '2025-01-01', 'mospi', 0.76), shareOfHeadline: 50 },
  { category: 'Fuel', contribution: observation('decomp-fuel', 'Fuel contribution', 0.6, 'percentage points', '2025-01-01', 'eia', 0.55), shareOfHeadline: 13 },
  { category: 'Core', contribution: observation('decomp-core', 'Core contribution', 1.8, 'percentage points', '2025-01-01', 'rbi-dbie', 0.67), shareOfHeadline: 37 },
];

export const mockInflationAnalysisKpis: Kpi[] = [
  { label: 'Headline CPI', value: `${mockCpiInflation.value.toFixed(1)}%`, change: 'Demo baseline', trend: 'flat', observation: mockCpiInflation },
  { label: 'Food inflation', value: `${mockFoodInflation.value.toFixed(1)}%`, change: 'Pressure', trend: 'up', observation: mockFoodInflation },
  { label: 'Core proxy', value: `${mockCoreInflation.value.toFixed(1)}%`, change: 'Below headline', trend: 'down', observation: mockCoreInflation },
  { label: 'Fuel / energy', value: `${mockInflationDecomposition[1].contribution.value.toFixed(1)} pp`, change: 'Watch channel', trend: 'flat', observation: mockInflationDecomposition[1].contribution },
];

export const mockInflationDrivers: InflationDriver[] = [
  { id: 'driver-food', title: 'Food prices', classification: 'pressure', summary: 'Food is the largest illustrative contribution to headline CPI in this demo snapshot.', observation: mockInflationDecomposition[0].contribution, sourceLabel: 'MoSPI' },
  { id: 'driver-fuel', title: 'Fuel and energy', classification: 'watch', summary: 'Energy costs are a smaller direct contribution here, but remain a monitored external-risk channel.', observation: mockInflationDecomposition[1].contribution, sourceLabel: 'EIA' },
  { id: 'driver-core', title: 'Core conditions', classification: 'offset', summary: 'The core proxy is below headline inflation in the illustrative dataset, moderating underlying pressure.', observation: mockCoreInflation, sourceLabel: 'RBI DBIE' },
];

export const mockInflationAnalysisNote: StaticAnalysisNote = {
  title: 'Static reading of the demo snapshot',
  text: 'The illustrative CPI snapshot is led by food contributions, while the core proxy is lower than headline inflation. Fuel and energy are presented as a monitored risk channel rather than a live shock assessment.',
  status: 'static-mock-analysis',
};

export const mockModelIntegrationNote: StaticAnalysisNote = {
  title: 'Model explanation unavailable',
  text: 'Model integration pending. This panel will later explain model-generated attribution, assumptions, and diagnostics when the model layer is connected.',
  status: 'model-integration-pending',
};

export const mockMacroSignals: MacroSignal[] = [
  { id: 'signal-food', label: 'Food pressure', direction: 'up', severity: 'medium', summary: 'Food prices remain the largest illustrative contributor to headline inflation.', observation: mockFoodInflation },
  { id: 'signal-growth', label: 'Growth momentum', direction: 'up', severity: 'low', summary: 'Domestic activity remains resilient in the demo baseline.', observation: mockGdpGrowth },
  { id: 'signal-fx', label: 'Currency watch', direction: 'flat', severity: 'medium', summary: 'The rupee path is stable in the current scenario assumptions.', observation: mockInrUsd },
];

export const mockPolicyScorecard: PolicyScorecardItem[] = [
  { dimension: 'Inflation alignment', score: 78, status: 'mock', rationale: 'Illustrative stance is broadly consistent with the target band.', confidence: 0.78 },
  { dimension: 'Growth support', score: 72, status: 'mock', rationale: 'Current settings preserve room for domestic demand resilience.', confidence: 0.7 },
  { dimension: 'External stability', score: 64, status: 'warning', rationale: 'Currency and energy assumptions carry wider uncertainty.', confidence: 0.58 },
  { dimension: 'Communication clarity', score: 84, status: 'mock', rationale: 'Forward guidance is coherent in the demo policy path.', confidence: 0.82 },
];

export const mockScenarioResults: ScenarioResult[] = [
  { id: 'hold', name: 'Hold at 6.50%', description: 'Maintain the current policy rate through the next review window.', repoRateChange: observation('scenario-hold-rate', 'Repo rate change', 0, 'percentage points', '2025-03-01', 'rbi-dbie', 0.72), inflation: observation('scenario-hold-inflation', 'Scenario inflation', 4.5, '% year-on-year', '2025-09-01', 'imf', 0.62), gdpGrowth: observation('scenario-hold-growth', 'Scenario GDP growth', 7.0, '% year-on-year', '2025-09-01', 'world-bank', 0.58), confidence: 0.66, status: 'mock' },
  { id: 'ease', name: 'Ease by 25 bps', description: 'Reduce the policy rate modestly as inflation expectations soften.', repoRateChange: observation('scenario-ease-rate', 'Repo rate change', -0.25, 'percentage points', '2025-03-01', 'rbi-dbie', 0.68), inflation: observation('scenario-ease-inflation', 'Scenario inflation', 4.8, '% year-on-year', '2025-09-01', 'imf', 0.58), gdpGrowth: observation('scenario-ease-growth', 'Scenario GDP growth', 7.3, '% year-on-year', '2025-09-01', 'world-bank', 0.56), confidence: 0.6, status: 'warning' },
  { id: 'tighten', name: 'Tighten by 25 bps', description: 'Increase the policy rate to contain a renewed food-price shock.', repoRateChange: observation('scenario-tighten-rate', 'Repo rate change', 0.25, 'percentage points', '2025-03-01', 'rbi-dbie', 0.68), inflation: observation('scenario-tighten-inflation', 'Scenario inflation', 4.1, '% year-on-year', '2025-09-01', 'imf', 0.56), gdpGrowth: observation('scenario-tighten-growth', 'Scenario GDP growth', 6.7, '% year-on-year', '2025-09-01', 'world-bank', 0.54), confidence: 0.57, status: 'warning' },
];

export const mockPolicyAlternativeAnalyses: PolicyAlternativeAnalysis[] = [
  {
    id: 'hike-50',
    title: 'Hike 50 bp',
    stance: 'Firm tightening',
    summary: 'The demo path prioritizes faster inflation control at the cost of weaker near-term demand support.',
    scorecard: [
      { dimension: 'Inflation control', score: 88, status: 'mock', rationale: 'Strongest illustrative disinflation impulse.', confidence: 0.62 },
      { dimension: 'Growth support', score: 43, status: 'warning', rationale: 'Tighter conditions weigh on the growth outlook.', confidence: 0.58 },
      { dimension: 'FX pressure', score: 76, status: 'mock', rationale: 'Higher rates provide relative currency support in the demo.', confidence: 0.51 },
      { dimension: 'Financial conditions', score: 38, status: 'warning', rationale: 'Financial conditions become materially tighter.', confidence: 0.56 },
      { dimension: 'Model uncertainty', score: 46, status: 'warning', rationale: 'Shock persistence and transmission are uncertain.', confidence: 0.44 },
    ],
    confidence: 0.56,
    evidence: [mockCpiInflation, mockFoodInflation, mockRepoRate],
    assumptions: ['Food-price pressure persists through the review horizon.', 'Rate transmission is gradual and broadly symmetric.'],
    warnings: ['Growth downside may be understated.', 'This is not an official policy recommendation.'],
    isRecommendedDemo: false,
  },
  {
    id: 'hold',
    title: 'Hold',
    stance: 'Wait and assess',
    summary: 'The demo path balances the current inflation reading with resilience in domestic activity while awaiting more evidence.',
    scorecard: [
      { dimension: 'Inflation control', score: 68, status: 'mock', rationale: 'Maintains the existing restrictive stance.', confidence: 0.66 },
      { dimension: 'Growth support', score: 78, status: 'mock', rationale: 'Avoids an additional near-term rate shock.', confidence: 0.68 },
      { dimension: 'FX pressure', score: 61, status: 'warning', rationale: 'Less rate support leaves external sensitivity.', confidence: 0.52 },
      { dimension: 'Financial conditions', score: 72, status: 'mock', rationale: 'Conditions remain stable relative to the baseline.', confidence: 0.65 },
      { dimension: 'Model uncertainty', score: 67, status: 'mock', rationale: 'Preserves optionality as new evidence arrives.', confidence: 0.61 },
    ],
    confidence: 0.66,
    evidence: [mockCpiInflation, mockCoreInflation, mockGdpGrowth],
    assumptions: ['Headline inflation gradually converges toward the illustrative target range.', 'No large additional external shock is introduced.'],
    warnings: ['Food inflation could remain persistent.', 'Currency and energy channels remain sensitive.'],
    isRecommendedDemo: true,
  },
  {
    id: 'cut-25',
    title: 'Cut 25 bp',
    stance: 'Modest easing',
    summary: 'The demo path supports activity but accepts greater risk that inflation and external pressures persist.',
    scorecard: [
      { dimension: 'Inflation control', score: 48, status: 'warning', rationale: 'Easing reduces the illustrative disinflation buffer.', confidence: 0.55 },
      { dimension: 'Growth support', score: 87, status: 'mock', rationale: 'Lower rates provide the strongest demand support.', confidence: 0.64 },
      { dimension: 'FX pressure', score: 43, status: 'warning', rationale: 'Lower rates increase currency sensitivity in the demo.', confidence: 0.49 },
      { dimension: 'Financial conditions', score: 86, status: 'mock', rationale: 'Financial conditions ease relative to the baseline.', confidence: 0.63 },
      { dimension: 'Model uncertainty', score: 39, status: 'warning', rationale: 'The inflation response is particularly assumption-sensitive.', confidence: 0.43 },
    ],
    confidence: 0.5,
    evidence: [mockCpiInflation, mockCoreInflation, mockInrUsd],
    assumptions: ['Core inflation remains contained despite easier conditions.', 'External funding conditions remain orderly.'],
    warnings: ['Upside inflation risk is material.', 'FX pressure may amplify imported inflation.'],
    isRecommendedDemo: false,
  },
];

export const mockAgentExecutionEvents: AgentExecutionEvent[] = [
  { id: 'event-001', timestamp: '2025-02-12T09:30:00Z', agent: 'Planner', event: 'Research task created', status: 'completed', durationMs: 420, details: 'Mock run initialized for the India inflation review.', toolCalls: ['create_research_run'], sourceReferences: [mockCpiInflation] },
  { id: 'event-002', timestamp: '2025-02-12T09:30:02Z', agent: 'Data', event: 'Source manifest loaded', status: 'completed', durationMs: 860, details: 'Loaded illustrative domestic and international source metadata.', toolCalls: ['load_source_manifest', 'validate_series_catalog'], sourceReferences: [mockCpiInflation, mockRepoRate, mockInrUsd] },
  { id: 'event-003', timestamp: '2025-02-12T09:30:04Z', agent: 'Inflation', event: 'Inflation signals prepared', status: 'completed', durationMs: 1240, details: 'Prepared mock CPI headline, food, core, and decomposition inputs.', toolCalls: ['read_cpi_series', 'decompose_inflation'], sourceReferences: [mockCpiInflation, mockFoodInflation, mockCoreInflation] },
  { id: 'event-004', timestamp: '2025-02-12T09:30:05Z', agent: 'Growth', event: 'Growth context prepared', status: 'completed', durationMs: 980, details: 'Prepared the illustrative domestic activity context.', toolCalls: ['read_growth_series'], sourceReferences: [mockGdpGrowth] },
  { id: 'event-005', timestamp: '2025-02-12T09:30:06Z', agent: 'External', event: 'External sector context prepared', status: 'warning', durationMs: 1110, details: 'Prepared FX and energy context with wider demo uncertainty.', toolCalls: ['read_fx_series', 'read_energy_series'], sourceReferences: [mockInrUsd], warnings: ['External data is mock-only and not refreshed.'] },
  { id: 'event-006', timestamp: '2025-02-12T09:30:08Z', agent: 'Econometrics', event: 'Model stage reserved', status: 'pending', details: 'Econometric model integration is not connected in this prototype.', warnings: ['No model output or hidden reasoning is available.'] },
  { id: 'event-007', timestamp: '2025-02-12T09:30:09Z', agent: 'Scenario', event: 'Scenario comparison staged', status: 'pending', details: 'Scenario inputs are represented by static mock results for now.', toolCalls: ['stage_scenario_comparison'] },
  { id: 'event-008', timestamp: '2025-02-12T09:30:10Z', agent: 'Policy', event: 'Policy comparison staged', status: 'pending', details: 'Policy alternatives are presented as mock comparative scorecards.', toolCalls: ['stage_policy_scorecard'] },
  { id: 'event-009', timestamp: '2025-02-12T09:30:11Z', agent: 'Critic', event: 'Validation flags recorded', status: 'warning', durationMs: 690, details: 'Recorded uncertainty flags for analyst review.', toolCalls: ['run_demo_validation'], warnings: ['Prototype status: no official recommendation.'] },
  { id: 'event-010', timestamp: '2025-02-12T09:30:12Z', agent: 'Report', event: 'Report draft staged', status: 'pending', details: 'Report output is available as mock content only.', toolCalls: ['stage_report_sections'] },
];

export const mockSavedReports: SavedReport[] = [
  { id: 'report-001', title: 'January inflation baseline', createdAt: '2025-02-12T09:45:00Z', author: 'Research workspace', status: 'ready', tags: ['CPI', 'baseline'], summary: 'Illustrative review of headline inflation and current policy assumptions.', question: 'What is driving the current illustrative CPI reading?', scenario: 'Baseline / hold', confidence: 0.66, sources: [mockCpiInflation, mockFoodInflation, mockCoreInflation], executiveSummary: 'Food contributions lead the demo inflation snapshot while the core proxy remains lower than headline CPI.', currentState: 'Headline CPI is shown at 4.8% year-on-year in the mock catalog.', forecast: 'The static forecast path trends gradually lower over the illustrative horizon.', scenarioAnalysis: 'The hold path preserves optionality while food-price pressure remains a watch item.', policyScorecard: mockPolicyScorecard, assumptions: ['All observations are static mock values.', 'No external API was queried.'], warnings: ['Not official RBI research.', 'Model integration is pending.'] },
  { id: 'report-002', title: 'Food shock scenario note', createdAt: '2025-02-10T14:20:00Z', author: 'Research workspace', status: 'draft', tags: ['scenario', 'food'], summary: 'Draft comparison of policy responses to a renewed food-price shock.', question: 'How might a food-price shock alter policy trade-offs?', scenario: 'Food inflation shock / hold', confidence: 0.52, sources: [mockFoodInflation, mockCpiInflation, mockRepoRate], executiveSummary: 'This draft compares illustrative inflation and growth trade-offs under a food shock.', currentState: 'Food inflation is represented as an elevated mock input.', forecast: 'No model forecast is connected; the page uses static scenario framing.', scenarioAnalysis: 'Tighter policy improves the illustrative inflation score but reduces growth support.', policyScorecard: mockPolicyScorecard, assumptions: ['Shock transmission is simplified.', 'The policy response is illustrative.'], warnings: ['Do not interpret as a policy forecast.'] },
  { id: 'report-003', title: 'External stability watch', createdAt: '2025-02-01T11:05:00Z', author: 'Research workspace', status: 'archived', tags: ['INR', 'energy'], summary: 'Archived demo note on exchange-rate and energy-risk assumptions.', question: 'Which external channels should be monitored?', scenario: 'External sector watch', confidence: 0.48, sources: [mockInrUsd, mockRepoRate], executiveSummary: 'The demo note tracks currency and energy channels as uncertainty sources.', currentState: 'INR/USD and energy observations are mock catalog entries.', forecast: 'No external forecast is connected in the prototype.', scenarioAnalysis: 'External stability is shown as sensitive to currency and energy assumptions.', policyScorecard: mockPolicyScorecard, assumptions: ['External observations are not refreshed.', 'No market data feed is connected.'], warnings: ['Archived mock report.', 'Not investment or policy advice.'] },
];
