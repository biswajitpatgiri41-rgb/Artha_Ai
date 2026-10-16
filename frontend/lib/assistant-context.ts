export interface AssistantPageContext {
  page: string;
  title: string;
  guidance: string[];
  suggestions: string[];
  defaultPageData: PageAssistantContext;
}

export interface PageAssistantMetric {
  label: string;
  value: string;
  source: string;
}

export interface PageAssistantContext {
  page: string;
  mode: 'mock' | 'live' | 'none';
  visibleMetrics: PageAssistantMetric[];
  selectedScenario: Record<string, string | number | boolean | null> | null;
  selectedSeries: Record<string, string | number | boolean | null> | null;
  warnings: string[];
  run_id?: string;
}

const livePageData = (page: string): PageAssistantContext => ({
  page,
  mode: 'live',
  visibleMetrics: [],
  selectedScenario: null,
  selectedSeries: null,
  warnings: ['The Overview uses validated project observations and stored model forecasts. Unavailable indicators are not substituted with mock values.'],
});

const mockPageData = livePageData;

const pageContexts: Record<string, AssistantPageContext> = {
  '/': {
    page: '/',
    title: 'Monetary Policy Overview',
    guidance: ['dashboard indicators', 'monetary-policy concepts', 'what each application section represents'],
    suggestions: ['What does the repo rate affect?', 'How should I read this dashboard?', 'What is the inflation-growth tradeoff?'],
    defaultPageData: livePageData('/'),
  },
  '/analysis': {
    page: '/analysis',
    title: 'Inflation Analysis',
    guidance: ['CPI, food, core, and fuel inflation', 'inflation decomposition', 'inflation transmission mechanisms'],
    suggestions: ["What's the difference between headline and core inflation?", 'Why can food inflation rise quickly?', 'How does oil affect CPI?'],
    defaultPageData: mockPageData('/analysis'),
  },
  '/forecasts': {
    page: '/forecasts',
    title: 'Forecast Analysis',
    guidance: ['forecast horizons and uncertainty intervals', 'MAE, RMSE, MAPE, and coverage', 'differences between model types'],
    suggestions: ['What does an 80% forecast interval mean?', "What's the difference between VAR and ARIMA?", 'Why is time-series backtesting important?'],
    defaultPageData: mockPageData('/forecasts'),
  },
  '/simulator': {
    page: '/simulator',
    title: 'Scenario Simulator',
    guidance: ['oil, food, INR, and rate shocks', 'scenario controls', 'interpreting displayed simulation results'],
    suggestions: ['What happens when oil rises?', 'How does INR depreciation affect inflation?', 'What does +50 bp mean?'],
    defaultPageData: mockPageData('/simulator'),
  },
  '/policy': {
    page: '/policy',
    title: 'Policy Recommendations',
    guidance: ['hike, hold, and cut tradeoffs', 'inflation-growth and FX implications', 'uncertainty and the policy scorecard'],
    suggestions: ['Why would a central bank hold rates?', 'What are the risks of hiking?', 'How does policy affect growth?'],
    defaultPageData: mockPageData('/policy'),
  },
  '/data': {
    page: '/data',
    title: 'Economic Data Explorer',
    guidance: ['series, units, frequency, and base year', 'sources, metadata, and provenance', 'whether connected data is real or illustrative'],
    suggestions: ['What does base year mean?', 'Why does data provenance matter?', 'What is YoY inflation?'],
    defaultPageData: mockPageData('/data'),
  },
  '/logs': {
    page: '/logs',
    title: 'Agent Execution Logs',
    guidance: ['agent statuses and operational events', 'tool calls, failures, and the execution pipeline', 'available execution information without chain-of-thought'],
    suggestions: ['What does the Critic Agent do?', 'What does RUNNING mean?', 'Why would an agent fail?'],
    defaultPageData: mockPageData('/logs'),
  },
  '/reports': {
    page: '/reports',
    title: 'Research Reports',
    guidance: ['report sections, evidence, and assumptions', 'warnings and sources'],
    suggestions: ['How should I read this report?', 'What do the warnings mean?', 'Why do sources and assumptions matter?'],
    defaultPageData: mockPageData('/reports'),
  },
  '/architecture': {
    page: '/architecture',
    title: 'System Architecture',
    guidance: ['FastAPI, LangGraph, agents, and data flow', 'deterministic tools, critic, and report generation', 'current component connectivity'],
    suggestions: ['How does data move through this system?', 'What does LangGraph do?', 'Why are numerical tools separate from the LLM?'],
    defaultPageData: mockPageData('/architecture'),
  },
};

export function getPageContext(pathname: string): AssistantPageContext {
  const matchingPath = Object.keys(pageContexts)
    .filter((path) => path === '/' ? pathname === '/' : pathname.startsWith(path))
    .sort((a, b) => b.length - a.length)[0];

  return pageContexts[matchingPath ?? '/'];
}
