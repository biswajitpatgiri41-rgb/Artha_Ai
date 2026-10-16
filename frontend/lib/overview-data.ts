import type { EconomicObservation, ForecastPoint, Kpi, TimeSeriesPoint } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

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
  const seriesIds = ['cpi_yoy', 'food_inflation', 'repo_rate', 'inr_usd'];
  const series = await Promise.all(seriesIds.map(async (id) => [id, await getJson<SeriesResponse>(`/series/${id}?limit=500`)] as const));
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
  const forecastResponses = await Promise.all([1, 3, 6, 12].map((horizon) =>
    getJson<ForecastResponse>(`/forecast/final?model=ensemble&variant=mospi_2024_base&horizon=${horizon}`),
  ));
  const forecast = forecastResponses.map((response) => {
    const item = response.forecasts[0];
    const interval = response.intervals?.['80'];
    const date = response.target_month ? `${response.target_month}-01` : '';
    return {
      id: `forecast-${item.step}`,
      label: 'Headline CPI forecast',
      period: date.slice(0, 7),
      date,
      value: item.value,
      lowerBound: interval?.lower ?? item.value,
      upperBound: interval?.upper ?? item.value,
      unit: response.unit,
      source: response.source,
      sourceUrl: '#',
      status: 'validated' as const,
      confidence: 1,
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
      { label: 'GDP Growth', value: 'Unavailable', change: 'No data', trend: 'flat' },
      makeKpi('INR/USD', 'inr_usd', 2),
    ],
    historical,
    forecast,
    headline: latestCpi ? observation('cpi_yoy', 'Headline CPI', latestCpi) : null,
    latestDate: latestCpi?.date ?? null,
  };
}
