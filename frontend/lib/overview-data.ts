import type { EconomicObservation, ForecastPoint, Kpi, TimeSeriesPoint } from './types';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://artha-ai-api.vercel.app').replace(/\/$/, '');

interface ApiObservation {
  date: string;
  value: number;
  source: string;
  unit: string;
  source_url?: string | null;
  retrieved_at?: string | null;
}

interface SeriesResponse {
  observations: ApiObservation[];
}

interface ForecastResponse {
  origin?: string;
  target_month?: string;
  forecasts: Array<{ step: number; value: number }>;
  intervals?: Record<string, { lower?: number; upper?: number }>;
  source: string;
  unit: string;
}

export interface OverviewData {
  kpis: Kpi[];
  historical: TimeSeriesPoint[];
  forecast: ForecastPoint[];
  headline: EconomicObservation | null;
  latestDate: string | null;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

function observation(id: string, label: string, row: ApiObservation): EconomicObservation {
  return {
    id,
    label,
    value: row.value,
    unit: row.unit,
    date: row.date,
    source: row.source,
    sourceUrl: row.source_url ?? '#',
    retrievedDate: row.retrieved_at?.slice(0, 10),
    status: 'validated',
    confidence: 1,
    isMock: false,
  };
}

function formatValue(value: number, digits: number): string {
  return Number.isFinite(value) ? value.toFixed(digits) : 'Unavailable';
}

export async function loadOverviewData(): Promise<OverviewData> {
  const seriesIds = ['cpi_yoy', 'food_inflation', 'repo_rate', 'india_gdp_growth_annual_wb', 'inr_usd'];
  const series = await Promise.all(seriesIds.map(async (id): Promise<readonly [string, SeriesResponse]> => {
    try { return [id, await getJson<SeriesResponse>(`/series/${id}?limit=500`)] as const; }
    catch { return [id, { observations: [] }] as const; }
  }));
  const byId = new Map(series);
  const cpiRows = byId.get('cpi_yoy')?.observations ?? [];
  const latestCpi = cpiRows.at(-1);
  const historical = cpiRows.slice(-36).map((row) => ({
    id: `cpi-${row.date}`,
    label: 'Headline CPI',
    period: row.date.slice(0, 7),
    date: row.date,
    value: row.value,
    unit: row.unit,
    source: row.source,
    sourceUrl: row.source_url ?? '#',
    retrievedDate: row.retrieved_at?.slice(0, 10),
    status: 'validated' as const,
    confidence: 1,
    isMock: false,
  }));
  let forecastResponse: ForecastResponse | null = null;
  if (cpiRows.length) {
    try { forecastResponse = await getJson<ForecastResponse>('/forecast?series_id=cpi_yoy&model=seasonal_naive&horizon=12'); }
    catch { forecastResponse = null; }
  }
  const forecastOrigin = forecastResponse?.origin ? new Date(`${forecastResponse.origin.slice(0, 7)}-01T00:00:00Z`) : null;
  const forecast = (forecastResponse?.forecasts ?? []).map((item) => {
    const date = forecastOrigin ? new Date(Date.UTC(forecastOrigin.getUTCFullYear(), forecastOrigin.getUTCMonth() + item.step, 1)).toISOString().slice(0, 10) : '';
    return {
      id: `forecast-${item.step}`,
      label: 'Headline CPI forecast',
      period: date.slice(0, 7),
      date,
      value: item.value,
      lowerBound: item.value,
      upperBound: item.value,
      unit: forecastResponse?.unit ?? 'percent',
      source: forecastResponse?.source ?? 'project API',
      sourceUrl: '#',
      status: 'validated' as const,
      confidence: 0,
      isMock: false,
      isForecast: true as const,
    };
  });

  const latest = (id: string) => byId.get(id)?.observations.at(-1);
  const makeKpi = (label: string, id: string, digits: number): Kpi => {
    const row = latest(id);
    if (!row) return { label, value: 'Unavailable', change: 'No data', trend: 'flat' };
    return {
      label,
      value: formatValue(row.value, digits),
      change: row.date.slice(0, 7),
      trend: 'flat',
      observation: observation(id, label, row),
      sparkline: (byId.get(id)?.observations ?? []).slice(-12).map((item) => item.value),
    };
  };
  return {
    kpis: [
      makeKpi('Headline CPI', 'cpi_yoy', 2),
      makeKpi('Food Inflation', 'food_inflation', 2),
      makeKpi('Repo Rate', 'repo_rate', 2),
      makeKpi('GDP Growth (annual)', 'india_gdp_growth_annual_wb', 2),
      makeKpi('INR/USD', 'inr_usd', 2),
    ],
    historical,
    forecast,
    headline: latestCpi ? observation('cpi_yoy', 'Headline CPI', latestCpi) : null,
    latestDate: latestCpi?.date ?? null,
  };
}
