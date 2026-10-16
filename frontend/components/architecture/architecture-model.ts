import type { Edge, Node } from '@xyflow/react';
import { Activity, BarChart3, BrainCircuit, Cloud, Database, FileOutput, Gauge, Globe2, Layers3, LineChart, Network, Search, Server, Settings2, ShieldCheck, Sparkles, Table2, UserRound, Waves, type LucideIcon } from 'lucide-react';

export type ArchitectureStatus = 'idle' | 'queued' | 'running' | 'completed' | 'warning' | 'failed';
export type ArchitectureCategory = 'source' | 'interface' | 'orchestration' | 'agent' | 'tool' | 'model' | 'explainability' | 'regime' | 'policy' | 'critic' | 'report' | 'storage' | 'evidence' | 'engineering' | 'evaluation' | 'scenario' | 'output';
export interface ArchitectureNodeData extends Record<string, unknown> { label: string; description: string; category: ArchitectureCategory; status: ArchitectureStatus; icon: LucideIcon; duration?: string; selected?: boolean; readiness?: 'connected' | 'planned' | 'model_pending' | 'data_pending'; }
export type ArchitectureNode = Node<ArchitectureNodeData, 'architecture'>;
export interface MacroSeriesPacket { type: 'macro_series'; series: string; source: string; observations: number; mock: true; }
export interface CommoditySeriesPacket { type: 'commodity_series'; series: string; source: string; mock: true; }
export interface ForecastPacket { type: 'forecast'; target: string; horizon: number; status: 'mock'; }
export interface ScenarioResultPacket { type: 'scenario_result'; oilShock: number; horizon: number; mock: true; }
export interface EvidencePacket { type: 'evidence'; evidence_id: string; filename: string; chunks: number; format: string; }
export type OperationalPacket = MacroSeriesPacket | CommoditySeriesPacket | ForecastPacket | ScenarioResultPacket | EvidencePacket;
export interface PacketInspection { edgeId: string; from: string; to: string; payload: OperationalPacket; timestamp: string; duration: string; }

const node = (id: string, label: string, description: string, category: ArchitectureCategory, icon: LucideIcon, x: number, y: number): ArchitectureNode => ({ id, type: 'architecture', position: { x, y }, data: { label, description, category, status: 'idle', icon } });
const edgeColors: Record<ArchitectureCategory, string> = { source: '#22d3ee', interface: '#22d3ee', orchestration: '#a78bfa', agent: '#a78bfa', tool: '#f59e0b', model: '#f59e0b', explainability: '#22d3ee', regime: '#a78bfa', policy: '#a78bfa', critic: '#fb7185', report: '#34d399', storage: '#60a5fa', evidence: '#2dd4bf', engineering: '#60a5fa', evaluation: '#a3e635', scenario: '#f472b6', output: '#34d399' };
const edge = (id: string, source: string, target: string, category: ArchitectureCategory = 'engineering', label?: string): Edge => ({ id, source, target, type: 'architecture', label, animated: false, data: { color: edgeColors[category] } });

const spaced = (ids: string[], labels: string[], category: ArchitectureCategory, icon: LucideIcon, y: number, description: string) => ids.map((id, i) => node(id, labels[i], description, category, icon, 30 + i * 195, y));

const plannedModule = (id: string, label: string, category: ArchitectureCategory, icon: LucideIcon, x: number, y: number, readiness: ArchitectureNodeData['readiness'] = 'planned') => ({ ...node(id, label, 'Planned module · no runtime output is represented', category, icon, x, y), data: { ...node(id, label, 'Planned module · no runtime output is represented', category, icon, x, y).data, readiness } });

// Advanced modules are intentionally unconnected until their runtime and data/model contracts are verified.
export const plannedArchitectureNodes: ArchitectureNode[] = [
  ...[
    ['Model Ensemble', 'Forecast Calibration', 'SHAP Explainability', 'Inflation Decomposition', 'Forecast Vintage Comparison'],
    ['Regime Detection', 'Local Projections', 'Impulse Response Functions', 'Nowcasting', 'Historical Counterfactuals'],
    ['Multi-Scenario Stress Testing', 'Monte Carlo Simulation', 'Inflation Risk Engine', 'Automatic Scenario Generator'],
    ['Taylor Rule Benchmark', 'Policy Optimization', 'Conditional Policy Paths'],
    ['Economic Knowledge Graph', 'Citation Validation'],
    ['Data Quality Monitor', 'Model Drift Detection', 'Champion/Challenger Registry', 'Agent Evaluation'],
  ].flatMap((labels, section) => labels.map((label, index) => {
    const sectionCategory: ArchitectureCategory[] = ['model', 'critic', 'scenario', 'policy', 'evidence', 'evaluation'];
    const icons: LucideIcon[] = [LineChart, Activity, Waves, Gauge, Network, ShieldCheck];
    const readiness = (label === 'Model Ensemble' || label === 'Forecast Calibration' || label === 'SHAP Explainability' || label === 'Regime Detection' || label === 'Monte Carlo Simulation' || label === 'Policy Optimization' || label === 'Model Drift Detection') ? 'model_pending' : 'planned';
    const category: ArchitectureCategory = label === 'SHAP Explainability' ? 'explainability' : label === 'Regime Detection' ? 'regime' : sectionCategory[section];
    return plannedModule(`planned-${section}-${index}`, label, category, icons[section], 30 + (index % 5) * 205, 2420 + section * 145, readiness);
  })),
];

export const sourceNodes = spaced(['source-mospi', 'source-rbi', 'source-eia', 'source-fred', 'source-imd', 'source-imf', 'source-world-bank'], ['MoSPI', 'RBI DBIE', 'EIA', 'FRED', 'IMD', 'IMF', 'World Bank'], 'source', Database, 30, 'Official economic data source');

export const initialArchitectureNodes: ArchitectureNode[] = [
  ...spaced(['adapter', 'raw-snapshots', 'validation', 'canonical-store', 'feature-engine'], ['Source Adapters', 'Raw Snapshots', 'Validation', 'Canonical Data Store', 'Feature Engine'], 'engineering', Database, 170, 'Deterministic data engineering'),
  ...spaced(['seasonal-naive', 'ets', 'sarima', 'sarimax', 'var', 'xgboost', 'ensemble'], ['Seasonal Naive', 'ETS', 'SARIMA', 'SARIMAX', 'VAR', 'XGBoost', 'Ensemble'], 'model', LineChart, 315, 'Deterministic numerical forecast model').map((item) => ({ ...item, data: { ...item.data, readiness: ['seasonal-naive', 'xgboost', 'ensemble'].includes(item.id) ? 'connected' as const : 'model_pending' as const } })),
  ...spaced(['rolling-backtest', 'final-holdout', 'forecast-metrics', 'interval-coverage', 'model-registry'], ['Rolling Backtest', 'Final Holdout', 'MAE / RMSE / Bias', 'Interval Coverage', 'Model Registry'], 'evaluation', BarChart3, 460, 'Quantitative model evaluation'),
  ...spaced(['baseline-forecast', 'shock-engine', 'monte-carlo', 'shocked-forecast', 'baseline-vs-shocked'], ['Baseline Forecast', 'Shock Engine', 'Monte Carlo Simulation', 'Shocked Forecast', 'Baseline vs Shocked'], 'scenario', Activity, 610, 'Scenario sensitivity and uncertainty'),
  node('shock-oil', 'Oil', 'Oil price shock', 'scenario', Waves, 225, 760),
  node('shock-fx', 'FX', 'Exchange rate shock', 'scenario', Globe2, 420, 760),
  node('shock-food', 'Food', 'Food price shock', 'scenario', Table2, 615, 760),
  node('shock-rate', 'Policy Rate', 'Policy rate shock', 'scenario', Gauge, 810, 760),
  ...[
    node('planner', 'Planner Agent', 'Plans the research run', 'agent', BrainCircuit, 30, 930),
    node('data-agent', 'Data Agent', 'Selects verified data and provenance', 'agent', Database, 260, 930),
    node('inflation-agent', 'Inflation Agent', 'Analyzes price dynamics', 'agent', Activity, 490, 1080),
    node('growth-agent', 'Growth Agent', 'Analyzes real activity', 'agent', LineChart, 720, 1080),
    node('external-agent', 'External Agent', 'Reviews external-sector pressures', 'agent', Globe2, 950, 1080),
    node('econometrics', 'Econometrics Agent', 'Interprets registered numerical outputs', 'agent', BarChart3, 1180, 930),
    node('policy', 'Policy Agent', 'Frames options and trade-offs', 'agent', Gauge, 1410, 930),
    node('critic', 'Critic Agent', 'Separate quantitative and evidence checks', 'critic', ShieldCheck, 1640, 930),
    node('report', 'Report Agent', 'Cites model output and documents separately', 'report', FileOutput, 1870, 930),
  ],
  node('llm-config', 'Configured NVIDIA LLM', 'Shared agent language model; never used as the numerical forecast engine', 'orchestration', BrainCircuit, 255, 1230),
  node('upload', 'User File Upload', 'Run scoped private evidence upload', 'evidence', UserRound, 30, 1450),
  node('format-router', 'Format Router', 'Routes each format to its safe parser', 'evidence', Network, 250, 1450),
  node('pdf-parser', 'PDF → Text Extraction', 'Page aware text extraction', 'evidence', FileOutput, 500, 1380),
  node('text-parser', 'TXT / MD → Text Extraction', 'Text and section aware extraction', 'evidence', FileOutput, 500, 1530),
  node('table-parser', 'CSV / XLSX → Table Tool', 'Deterministic structured data operations', 'evidence', Table2, 500, 1680),
  node('json-parser', 'JSON → Structured JSON Tool', 'Safe path and record operations', 'evidence', Database, 500, 1830),
  node('chunking', 'Cleaning & Chunking', 'Bounded text chunks with overlap and citations', 'evidence', Sparkles, 750, 1430),
  node('embeddings', 'Embedding Provider', 'Independent configurable embedding model', 'evidence', BrainCircuit, 980, 1430),
  node('vector-store', 'Run Scoped Vector Store', 'Persistent vectors isolated by run', 'evidence', Database, 1210, 1430),
  node('retriever', 'Evidence Retrieval', 'Returns relevant passages with source locations', 'evidence', Search, 1440, 1530),
  node('retrieved-evidence', 'Retrieved Evidence', 'Cited passages and structured results; no forecast generation', 'evidence', FileOutput, 1670, 1530),
  node('quant-validation', 'Quantitative Validation', 'Backtesting · holdout · metrics · intervals', 'critic', BarChart3, 1230, 1960),
  node('evidence-validation', 'Evidence Validation', 'Uploaded documents · citations · RAG retrieval', 'critic', Search, 1460, 1960),
  node('fastapi', 'FastAPI', 'Research and evidence API', 'output', Server, 1640, 2190),
  node('nextjs', 'Next.js Research Terminal', 'Dashboard, analysis, forecasts, backtesting, scenarios, policy, data, evidence, logs, architecture and reports', 'output', Layers3, 1880, 2190),
  node('pages', 'Research Pages', 'Dashboard · Inflation Analysis · Forecasts · Backtesting · Scenario Simulator · Policy · Data Explorer · Evidence Workspace · Agent Logs · System Architecture · Reports', 'output', Cloud, 2120, 2190),
];

export const initialArchitectureEdges: Edge[] = [
  ...sourceNodes.map((source) => edge(`${source.id}-adapter`, source.id, 'adapter', 'source')),
  edge('adapter-raw', 'adapter', 'raw-snapshots', 'engineering'), edge('raw-validation', 'raw-snapshots', 'validation', 'engineering'), edge('validation-canonical', 'validation', 'canonical-store', 'engineering'), edge('canonical-feature', 'canonical-store', 'feature-engine', 'engineering'),
  edge('feature-seasonal-naive', 'feature-engine', 'seasonal-naive', 'model'),
  // Current runtime exposes seasonal-naive and frozen CPI research forecasts; other model/evaluation boxes are not runtime-connected.
  edge('seasonal-naive-backtest', 'seasonal-naive', 'rolling-backtest', 'evaluation'),
  edge('seasonal-naive-metrics', 'seasonal-naive', 'forecast-metrics', 'evaluation'),
  edge('seasonal-naive-baseline', 'seasonal-naive', 'baseline-forecast', 'model'), edge('shock-result', 'shock-engine', 'shocked-forecast', 'scenario'),
  ...['shock-oil', 'shock-fx', 'shock-food', 'shock-rate'].map((id) => edge(`shock-input-${id}`, id, 'shock-engine', 'scenario')),
  edge('upload-router', 'upload', 'format-router', 'evidence'), edge('router-pdf', 'format-router', 'pdf-parser', 'evidence'), edge('router-text', 'format-router', 'text-parser', 'evidence'), edge('router-table', 'format-router', 'table-parser', 'evidence'), edge('router-json', 'format-router', 'json-parser', 'evidence'),
  edge('pdf-chunks', 'pdf-parser', 'chunking', 'evidence'), edge('text-chunks', 'text-parser', 'chunking', 'evidence'), edge('chunks-embeddings', 'chunking', 'embeddings', 'evidence'), edge('embeddings-store', 'embeddings', 'vector-store', 'evidence'), edge('store-retrieval', 'vector-store', 'retriever', 'evidence'), edge('retrieval-evidence', 'retriever', 'retrieved-evidence', 'evidence'), edge('table-evidence', 'table-parser', 'retrieved-evidence', 'evidence'), edge('json-evidence', 'json-parser', 'retrieved-evidence', 'evidence'),
  edge('retrieved-critic', 'retrieved-evidence', 'evidence-validation', 'critic'), edge('retrieved-report', 'retrieved-evidence', 'report', 'evidence'), edge('quant-critic', 'quant-validation', 'critic', 'critic'), edge('evidence-check-critic', 'evidence-validation', 'critic', 'critic'), edge('eval-roll', 'rolling-backtest', 'quant-validation', 'evaluation'), edge('eval-metrics', 'forecast-metrics', 'quant-validation', 'evaluation'),
  edge('critic-report', 'critic', 'report', 'report'), edge('report-api', 'report', 'fastapi', 'output'), edge('api-ui', 'fastapi', 'nextjs', 'output'), edge('ui-pages', 'nextjs', 'pages', 'output'),
];

export const architectureNodes = [...sourceNodes, ...initialArchitectureNodes, ...plannedArchitectureNodes];
export const architectureEdges = initialArchitectureEdges;
export const demoSequence = ['planner', 'data-agent', 'inflation-agent', 'growth-agent', 'external-agent', 'econometrics', 'policy', 'critic', 'report'];
export const demoEdges = ['planner-data-agent', 'data-inflation', 'inflation-econometrics', 'econometrics-policy', 'policy-critic', 'critic-report'];
export const packetInspections: Record<string, PacketInspection> = {
  'source-rbi-adapter': { edgeId: 'source-rbi-adapter', from: 'RBI DBIE', to: 'Source Adapters', payload: { type: 'macro_series', series: 'cpi_yoy', source: 'RBI DBIE', observations: 0, mock: true }, timestamp: '', duration: '' },
  'ensemble-baseline': { edgeId: 'ensemble-baseline', from: 'Deterministic Model Registry', to: 'Baseline Forecast', payload: { type: 'forecast', target: 'cpi_yoy', horizon: 6, status: 'mock' }, timestamp: '', duration: '' },
};
