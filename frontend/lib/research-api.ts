// Browser requests must target the deployed FastAPI service. Override this in
// each frontend deployment when using a different API domain.
export const apiBaseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://artha-ai-api.vercel.app').replace(/\/$/, '');

export interface ApiHealth {
  status: string;
  llm: 'configured' | 'not_configured';
  data: string;
  available_series: number;
  econometrics: string;
  final_model_package: string;
}

export async function getApiHealth(): Promise<ApiHealth> {
  const response = await fetch(`${apiBaseUrl}/health`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Health API returned ${response.status}`);
  return response.json() as Promise<ApiHealth>;
}

export interface SimulationResponse {
  mode: 'illustrative_sensitivity';
  baseline_inflation: number;
  scenario_inflation: number;
  change_pp: number;
  horizon_months: number;
  effects_pp: { oil: number; inr: number; food: number; repo: number };
  warnings: string[];
}

export async function simulateResearchScenario(input: {
  base_inflation: number; oil_change_pct: number; inr_change_pct: number;
  food_shock_pp: number; repo_change_bp: number; horizon_months: number;
}): Promise<SimulationResponse> {
  const response = await fetch(`${apiBaseUrl}/simulate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input), cache: 'no-store',
  });
  if (!response.ok) throw new Error(`Scenario API returned ${response.status}`);
  return response.json() as Promise<SimulationResponse>;
}

export interface ForecastResponse {
  series_id: string; model: string; status: string; mode: string; origin: string;
  horizon_months: number; forecasts: Array<{ step: number; value: number }>;
  source_observations: number; source: string; unit: string; warnings: string[];
  variant?: string; target_month?: string; dataset_start?: string; dataset_end?: string;
  component_forecasts?: Record<string, number>;
  model_weights?: Record<string, number>;
  package_created_at?: string;
  intervals?: Record<string, { lower: number | null; upper: number | null }>;
  calibration?: { coverage_80: number | null; coverage_95: number | null; status: string; model_version: string } | null;
}

export async function getBaselineForecast(horizon: number, model = 'seasonal_naive', variant = 'base'): Promise<ForecastResponse> {
  const query = new URLSearchParams({ series_id: 'cpi_yoy', horizon: String(horizon), model, variant });
  const response = await fetch(`${apiBaseUrl}/forecast?${query.toString()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(response.status === 409 ? 'India CPI observations are not available yet.' : `Forecast API returned ${response.status}`);
  return response.json() as Promise<ForecastResponse>;
}

export async function getFinalPackageForecast(horizon: number, model = 'ensemble', variant = 'mospi_2024_base'): Promise<ForecastResponse> {
  const query = new URLSearchParams({ horizon: String(horizon), model, variant });
  const response = await fetch(`${apiBaseUrl}/forecast/final?${query.toString()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(response.status === 404 ? 'No stored forecast is available for this model and horizon.' : `Final forecast API returned ${response.status}`);
  return response.json() as Promise<ForecastResponse>;
}

export interface FinalModelExplanation {
  model_version: string;
  method: 'shap';
  contributions: Array<{ feature: string; contribution: number; unit?: string }>;
  warnings: string[];
}

export async function getFinalModelExplanation(horizon: number, model: string, variant: string): Promise<FinalModelExplanation | null> {
  const query = new URLSearchParams({ horizon: String(horizon), model, variant });
  const response = await fetch(`${apiBaseUrl}/forecast/final/explainability?${query.toString()}`, { cache: 'no-store' });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Forecast explanation API returned ${response.status}`);
  return response.json() as Promise<FinalModelExplanation>;
}

export interface PackagedModelMetric {
  model: string; model_label: string; variant: string; horizon_months: number;
  test_origins: number; mae_pp: number; rmse_pp: number; bias_pp: number;
  test_start: string | null; test_end: string | null;
  coverage_80?: number | null; coverage_95?: number | null; model_weight?: number | null;
}

export interface PackagedModelRegistry {
  status: string; mode: string; target: string; unit: string; variants: string[];
  models?: string[];
  supported_horizons_months: number[];
  test_period: { months: number; start: string; end: string } | null;
  metrics: PackagedModelMetric[]; warnings: string[];
}

export async function getFinalModelRegistry(): Promise<PackagedModelRegistry> {
  const response = await fetch(`${apiBaseUrl}/forecast/final/models`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Final model registry returned ${response.status}`);
  return response.json() as Promise<PackagedModelRegistry>;
}

export interface P2BenchmarkRegistry {
  status: string;
  mode: string;
  source_repository: string;
  source_commit: string;
  source_license: string;
  dataset_sha256: string;
  dataset_start: string;
  dataset_end: string;
  target: string;
  training_observations: number;
  supported_horizons_months: number[];
  models: Record<string, string>;
  training_versions: Record<string, string>;
  metrics: Array<{
    model: string;
    test_start: string;
    test_end: string;
    test_observations: number;
    mae_percentage_points: number;
    rmse_percentage_points: number;
  }>;
  warnings: string[];
}

export async function getP2BenchmarkRegistry(): Promise<P2BenchmarkRegistry> {
  const response = await fetch(`${apiBaseUrl}/forecast/p2/models`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`P2 benchmark registry returned ${response.status}`);
  return response.json() as Promise<P2BenchmarkRegistry>;
}

export async function getP2BenchmarkForecast(model: string): Promise<ForecastResponse> {
  const query = new URLSearchParams({ model, horizon: '1' });
  const response = await fetch(`${apiBaseUrl}/forecast/p2?${query.toString()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`P2 benchmark forecast returned ${response.status}`);
  return response.json() as Promise<ForecastResponse>;
}

export interface ProjectSeriesCatalogItem {
  id: string; description: string; source: string; unit: string; base_year: string | null;
  frequency: string; enabled: boolean; available: boolean; observation_count: number;
  latest: { date: string; value: number; source: string; source_url?: string | null } | null;
}

export async function getProjectSeriesCatalog(): Promise<ProjectSeriesCatalogItem[]> {
  const response = await fetch(`${apiBaseUrl}/series`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Series catalog returned ${response.status}`);
  const payload = await response.json() as { series?: ProjectSeriesCatalogItem[] };
  return payload.series ?? [];
}

export async function getProjectSeriesObservations(seriesId: string, limit = 500): Promise<Array<{ date: string; value: number; source: string; unit: string }>> {
  const query = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`${apiBaseUrl}/series/${encodeURIComponent(seriesId)}?${query}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Series observations returned ${response.status}`);
  const payload = await response.json() as { observations?: Array<{ date: string; value: number; source: string; unit: string }> };
  return payload.observations ?? [];
}

export async function getPackagedModelRegistry(): Promise<PackagedModelRegistry> {
  const response = await fetch(`${apiBaseUrl}/forecast/models`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Packaged model registry returned ${response.status}`);
  return response.json() as Promise<PackagedModelRegistry>;
}

export interface BacktestResponse {
  series_id: string; model: string; horizon_months: number; origins: number;
  mae: number; rmse: number; bias: number; coverage_80: number | null;
  coverage_95: number | null; data_start: string; data_end: string; warnings: string[];
}

export async function getBaselineBacktest(horizon: number): Promise<BacktestResponse> {
  const response = await fetch(`${apiBaseUrl}/backtest?series_id=cpi_yoy&horizon=${horizon}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(response.status === 409 ? 'Not enough India CPI observations for rolling-origin backtesting.' : `Backtest API returned ${response.status}`);
  return response.json() as Promise<BacktestResponse>;
}

export interface ResearchRunResponse {
  run_id: string;
  status: string;
  created_at: string;
  question: string;
  data_vintage: string | null;
  forecast: ForecastResponse | null;
  backtest: BacktestResponse | null;
  scenarios: Array<Record<string, unknown>>;
  events: Array<{ node_id: string; status: string; message: string; timestamp: string }>;
  report: { title?: string; executive_summary?: string; current_state?: string; assumptions: string[]; warnings: string[] };
}

export async function getResearchRuns(): Promise<ResearchRunResponse[]> {
  const response = await fetch(`${apiBaseUrl}/research?limit=50`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Could not load research runs (HTTP ${response.status})`);
  const payload = await response.json() as { runs?: ResearchRunResponse[] };
  return payload.runs ?? [];
}

export async function createResearchRun(question: string, horizon = 6): Promise<ResearchRunResponse> {
  const response = await fetch(`${apiBaseUrl}/research`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question, horizon_months: horizon,
      scenarios: [],
    }),
  });
  if (!response.ok) throw new Error(`Research API returned ${response.status}`);
  return response.json() as Promise<ResearchRunResponse>;
}
