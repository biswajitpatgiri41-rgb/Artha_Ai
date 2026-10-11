export type PageStatus = 'planned' | 'ready';
export type MockStatus = 'mock' | 'validated' | 'warning' | 'error' | 'archived';
export type TrendDirection = 'up' | 'down' | 'flat';
export type SignalSeverity = 'low' | 'medium' | 'high';

export interface ObservationMetadata {
  value: number;
  unit: string;
  date: string;
  source: string;
  sourceUrl: string;
  retrievedDate?: string;
  status: MockStatus;
  confidence: number;
  isMock: boolean;
  note?: string;
}

export interface EconomicObservation extends ObservationMetadata {
  id: string;
  label: string;
}

export interface Kpi {
  label: string;
  value: string;
  change: string;
  trend: TrendDirection;
  observation?: EconomicObservation;
  sparkline?: number[];
}

export interface MacroObservation {
  period: string;
  inflation: number;
  repoRate: number;
  growth: number;
}

export interface TimeSeriesPoint extends EconomicObservation {
  period: string;
}

export interface ForecastPoint extends TimeSeriesPoint {
  lowerBound: number;
  upperBound: number;
  isForecast: true;
}

export interface InflationDecompositionItem {
  category: string;
  contribution: EconomicObservation;
  shareOfHeadline: number;
}

export interface InflationDriver {
  id: string;
  title: string;
  classification: 'pressure' | 'offset' | 'watch';
  summary: string;
  observation: EconomicObservation;
  sourceLabel: string;
}

export interface StaticAnalysisNote {
  title: string;
  text: string;
  status: 'static-mock-analysis' | 'model-integration-pending';
}

export interface MacroSignal {
  id: string;
  label: string;
  direction: TrendDirection;
  severity: SignalSeverity;
  summary: string;
  observation: EconomicObservation;
}

export interface PolicyScorecardItem {
  dimension: string;
  score: number;
  status: MockStatus;
  rationale: string;
  confidence: number;
}

export interface ScenarioResult {
  id: string;
  name: string;
  description: string;
  repoRateChange: EconomicObservation;
  inflation: EconomicObservation;
  gdpGrowth: EconomicObservation;
  confidence: number;
  status: MockStatus;
}

export interface PolicyAlternativeAnalysis {
  id: PolicyAlternative;
  title: string;
  stance: string;
  summary: string;
  scorecard: PolicyScorecardItem[];
  confidence: number;
  evidence: EconomicObservation[];
  assumptions: string[];
  warnings: string[];
  isRecommendedDemo: boolean;
}

export type PolicyAlternative = 'hike-50' | 'hold' | 'cut-25';

export interface SimulatorInputs {
  oilPriceShock: number;
  inrShock: number;
  foodInflationShock: number;
  policyRateChangeBp: number;
  horizonMonths: number;
  policyAlternative: PolicyAlternative;
}

export interface SimulatorResult {
  baselineInflation: number;
  scenarioInflation: number;
  potentialGrowthImpact: number;
  fxPressure: number;
  uncertainty: number;
  distribution: number[];
  policyScorecard: PolicyScorecardItem[];
  interpretation: string;
  isDemo: true;
}

export interface AgentExecutionEvent {
  id: string;
  timestamp: string;
  agent: string;
  event: string;
  status: 'pending' | 'queued' | 'running' | 'completed' | 'warning' | 'failed';
  durationMs?: number;
  details: string;
  toolCalls?: string[];
  sourceReferences?: EconomicObservation[];
  warnings?: string[];
}

export interface DataSource {
  id: string;
  name: string;
  provider: string;
  url: string;
  cadence: string;
  coverage: string;
  status: MockStatus;
  isMock: true;
}

export type SeriesFrequency = 'Daily' | 'Weekly' | 'Monthly' | 'Quarterly' | 'Annual' | 'Seasonal';

export interface SeriesObservation {
  date: string;
  value: number;
}

export interface MacroSeries {
  id: string;
  name: string;
  description: string;
  latestValue: number;
  unit: string;
  frequency: SeriesFrequency;
  source: string;
  sourceUrl: string;
  baseYear: string | null;
  latestObservation: string;
  status: MockStatus;
  seasonalAdjustment: string;
  retrievedDate: string;
  observations: SeriesObservation[];
  isMock: boolean;
}

export interface SavedReport {
  id: string;
  title: string;
  createdAt: string;
  author: string;
  status: 'draft' | 'ready' | 'archived';
  tags: string[];
  summary: string;
  question: string;
  scenario: string;
  confidence: number;
  sources: EconomicObservation[];
  executiveSummary: string;
  currentState: string;
  forecast: string;
  scenarioAnalysis: string;
  policyScorecard: PolicyScorecardItem[];
  assumptions: string[];
  warnings: string[];
}

export interface NavigationItem {
  label: string;
  href: string;
  status: PageStatus;
}
