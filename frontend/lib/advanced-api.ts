const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export type RegimeName = 'NORMAL INFLATION' | 'SUPPLY-SHOCK INFLATION' | 'DEMAND PRESSURE' | 'STAGFLATION';
export interface RegimeEvidence { source: string; reference: string; excerpt?: string | null; }
export interface RegimeRecord { regime: RegimeName; start_date: string | null; end_date: string | null; probability: number; model_version: string; data_vintage: string; evidence: RegimeEvidence[]; warnings: string[]; }
export interface RegimeResponse { status: string; regimes: RegimeRecord[]; warnings: string[]; }
export interface RegisteredModel { model_name: string; version: string; target: string; forecast_horizons: number[]; training_cutoff: string; data_vintage: string; feature_list: string[]; hyperparameters: Record<string, unknown>; backtest_metrics: Record<string, number>; artifact_hash: string; library_versions: Record<string, string>; git_commit?: string | null; status: 'CANDIDATE' | 'CHALLENGER' | 'CHAMPION' | 'REJECTED' | 'ARCHIVED'; created_at: string; }
export interface RegistryResponse { status: string; models: RegisteredModel[]; warnings: string[]; }
export interface DataQualitySeries { series_id: string; source: string; health: 'HEALTHY' | 'WARNING' | 'STALE' | 'FAILED' | 'NOT CONFIGURED'; last_observation: string | null; last_retrieval: string | null; release_date: string | null; data_vintage: string | null; observation_count: number; unit: string | null; base_year: string | null; validation_issues: string[] | null; checks: Record<string, boolean | null>; note: string; }
export interface DataQualityResponse { as_of: string; series: DataQualitySeries[]; validation_reports: Array<Record<string, unknown> & { report_id: string }>; warnings: string[]; }

async function getJson<T>(path: string): Promise<T> { const response = await fetch(`${apiBase}${path}`, { cache: 'no-store' }); if (!response.ok) throw new Error(`API request failed (${response.status})`); return response.json() as Promise<T>; }
export const getRegimes = () => getJson<RegimeResponse>('/regimes');
export const getModelRegistry = () => getJson<RegistryResponse>('/models/registry');
export const getDataQuality = () => getJson<DataQualityResponse>('/data-quality');
