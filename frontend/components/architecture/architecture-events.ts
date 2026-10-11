import type { ArchitectureStatus } from './architecture-model';

export type ArchitectureEventType =
  | 'run_started'
  | 'node_queued'
  | 'node_started'
  | 'node_completed'
  | 'node_failed'
  | 'edge_transfer'
  | 'tool_called'
  | 'tool_completed'
  | 'critic_failed'
  | 'run_completed';

export type EvidenceArchitectureEventType = 'evidence_upload_started' | 'evidence_uploaded' | 'evidence_deleted' | 'evidence_parsing_started' | 'evidence_parsing_completed' | 'evidence_indexed' | 'evidence_ready' | 'evidence_processing_failed' | 'retrieval_started' | 'retrieval_completed' | 'evidence_validation_started' | 'evidence_validation_completed' | 'critic_started' | 'critic_completed' | 'report_started' | 'report_completed';

export interface ArchitectureEvent {
  runId: string;
  timestamp: string;
  type: ArchitectureEventType | EvidenceArchitectureEventType;
  nodeId?: string;
  sourceNodeId?: string;
  targetNodeId?: string;
  message: string;
  payload?: Record<string, unknown>;
  durationMs?: number;
}

export type ArchitecturePhase = 'idle' | 'running' | 'complete';
export type EdgeRuntimeStatus = 'idle' | 'active' | 'completed' | 'failed';

export interface ArchitectureEventLogEntry {
  id: string;
  timestamp: string;
  node: string;
  type: 'data' | 'agents' | 'tools' | 'policy' | 'errors';
  message: string;
  duration?: string;
}

export interface ArchitectureEventState {
  runId: string;
  nodeStatuses: Record<string, ArchitectureStatus>;
  edgeStatuses: Record<string, EdgeRuntimeStatus>;
  activeEdgeIds: string[];
  eventLog: ArchitectureEventLogEntry[];
  eventLabel: string;
  elapsedMs: number;
  running: boolean;
  phase: ArchitecturePhase;
  currentStep: number;
  totalSteps: number;
  currentNode: string;
  criticResult?: 'passed' | 'failed';
  lastEvent?: ArchitectureEvent;
}

const eventCategory = (event: ArchitectureEvent): ArchitectureEventLogEntry['type'] => {
  if (event.type.startsWith('evidence_') || event.type.startsWith('retrieval_')) return 'tools';
  if (event.type === 'tool_called' || event.type === 'tool_completed') return 'tools';
  if (event.type === 'critic_failed') return 'errors';
  if (event.type === 'run_completed') return 'policy';
  if (event.nodeId?.includes('agent') || event.nodeId === 'planner' || event.nodeId === 'orchestrator') return 'agents';
  return event.type === 'edge_transfer' ? 'data' : 'agents';
};

const displayNode = (event: ArchitectureEvent) => event.nodeId ?? event.sourceNodeId ?? 'System';
const displayDuration = (durationMs?: number) => durationMs === undefined ? undefined : durationMs >= 1000 ? `${(durationMs / 1000).toFixed(2)} s` : `${durationMs} ms`;

export function createInitialArchitectureEventState(runId = 'idle'): ArchitectureEventState {
  return { runId, nodeStatuses: {}, edgeStatuses: {}, activeEdgeIds: [], eventLog: [], eventLabel: 'Ready to run', elapsedMs: 0, running: false, phase: 'idle', currentStep: 0, totalSteps: 14, currentNode: '' };
}

export function reduceArchitectureEvent(state: ArchitectureEventState, event: ArchitectureEvent): ArchitectureEventState {
  const next: ArchitectureEventState = {
    ...state,
    runId: event.runId,
    lastEvent: event,
    eventLabel: event.message,
    activeEdgeIds: [],
    elapsedMs: Math.max(state.elapsedMs, Date.parse(event.timestamp) - Date.parse(state.eventLog[0]?.timestamp ?? event.timestamp)),
  };
  const logEntry: ArchitectureEventLogEntry = { id: `${event.runId}-${state.eventLog.length}`, timestamp: event.timestamp, node: displayNode(event), type: eventCategory(event), message: event.message, duration: displayDuration(event.durationMs) };
  if (event.type !== 'node_queued' && event.type !== 'node_started') next.eventLog = [...state.eventLog, logEntry];

  switch (event.type) {
    case 'evidence_upload_started':
      next.nodeStatuses = { ...state.nodeStatuses, upload: 'running' };
      next.activeEdgeIds = ['upload-router']; next.phase = 'running'; next.running = true; break;
    case 'evidence_uploaded':
      next.nodeStatuses = { ...state.nodeStatuses, upload: 'completed', 'format-router': 'running' };
      next.activeEdgeIds = ['upload-router']; next.phase = 'running'; next.running = true; break;
    case 'evidence_deleted':
      next.nodeStatuses = { ...state.nodeStatuses, 'vector-store': 'completed', upload: 'completed' };
      next.activeEdgeIds = []; next.phase = 'complete'; next.running = false; break;
    case 'evidence_parsing_started': {
      const format = String(event.payload?.format ?? '').toLowerCase();
      const parser = format === 'pdf' ? 'pdf-parser' : format === 'txt' || format === 'md' ? 'text-parser' : format === 'csv' || format === 'xlsx' ? 'table-parser' : 'json-parser';
      const fromEdge = `router-${parser.replace('-parser', '')}`;
      next.nodeStatuses = { ...state.nodeStatuses, 'format-router': 'completed', [parser]: 'running' };
      next.activeEdgeIds = [fromEdge]; next.phase = 'running'; next.running = true; break;
    }
    case 'evidence_parsing_completed': {
      const format = String(event.payload?.format ?? '').toLowerCase();
      const parser = format === 'pdf' ? 'pdf-parser' : format === 'txt' || format === 'md' ? 'text-parser' : format === 'csv' || format === 'xlsx' ? 'table-parser' : 'json-parser';
      next.nodeStatuses = { ...state.nodeStatuses, [parser]: 'completed' };
      next.activeEdgeIds = format === 'pdf' ? ['pdf-chunks'] : format === 'txt' || format === 'md' ? ['text-chunks'] : [format === 'csv' || format === 'xlsx' ? 'router-table' : 'router-json'];
      next.phase = 'running'; next.running = true; break;
    }
    case 'evidence_indexed':
      next.nodeStatuses = { ...state.nodeStatuses, 'pdf-parser': 'completed', 'text-parser': 'completed', chunking: 'completed', embeddings: 'completed', 'vector-store': 'completed' };
      next.activeEdgeIds = ['pdf-chunks', 'text-chunks', 'chunks-embeddings', 'embeddings-store']; next.phase = 'complete'; next.running = false; break;
    case 'evidence_ready':
      next.phase = 'complete'; next.running = false; break;
    case 'evidence_processing_failed': {
      const format = String(event.payload?.format ?? '').toLowerCase();
      const parser = format === 'pdf' ? 'pdf-parser' : format === 'txt' || format === 'md' ? 'text-parser' : format === 'csv' || format === 'xlsx' ? 'table-parser' : 'json-parser';
      next.nodeStatuses = { ...state.nodeStatuses, [parser]: 'failed' };
      next.phase = 'complete'; next.running = false; break;
    }
    case 'retrieval_started':
      next.nodeStatuses = { ...state.nodeStatuses, retriever: 'running' };
      next.activeEdgeIds = ['store-retrieval']; next.phase = 'running'; next.running = true; break;
    case 'retrieval_completed':
      next.nodeStatuses = { ...state.nodeStatuses, retriever: 'completed', 'retrieved-evidence': 'completed' };
      next.activeEdgeIds = ['retrieval-evidence']; next.phase = 'complete'; next.running = false; break;
    case 'evidence_validation_started':
      next.nodeStatuses = { ...state.nodeStatuses, 'evidence-validation': 'running', critic: 'running' };
      next.activeEdgeIds = ['retrieved-critic', 'evidence-check-critic']; next.phase = 'running'; next.running = true; break;
    case 'evidence_validation_completed':
      next.nodeStatuses = { ...state.nodeStatuses, 'evidence-validation': 'completed', critic: event.payload?.valid === false ? 'warning' : 'completed' };
      next.activeEdgeIds = ['evidence-check-critic']; next.phase = 'complete'; next.running = false; break;
    case 'critic_started':
      next.nodeStatuses = { ...state.nodeStatuses, critic: 'running' };
      next.phase = 'running'; next.running = true; break;
    case 'critic_completed':
      next.nodeStatuses = { ...state.nodeStatuses, critic: event.payload?.overall_status === 'PASS' ? 'completed' : 'warning' };
      next.activeEdgeIds = ['critic-report']; next.phase = 'running'; next.running = true; break;
    case 'report_started':
      next.nodeStatuses = { ...state.nodeStatuses, report: 'running' };
      next.activeEdgeIds = ['critic-report']; next.phase = 'running'; next.running = true; break;
    case 'report_completed':
      next.nodeStatuses = { ...state.nodeStatuses, report: 'completed' };
      next.activeEdgeIds = ['report-api']; next.phase = 'complete'; next.running = false; break;
    case 'run_started':
      next.phase = 'running'; next.running = true; next.currentStep = 0; next.currentNode = ''; next.eventLog = [logEntry]; break;
    case 'node_queued':
      if (event.nodeId) next.nodeStatuses = { ...state.nodeStatuses, [event.nodeId]: 'queued' }; next.currentNode = event.nodeId ?? ''; next.currentStep = Math.max(state.currentStep, Number(event.payload?.step ?? state.currentStep)); break;
    case 'node_started':
      if (event.nodeId) next.nodeStatuses = { ...state.nodeStatuses, [event.nodeId]: 'running' }; next.currentNode = event.nodeId ?? ''; next.running = true; next.phase = 'running'; break;
    case 'node_completed':
      if (event.nodeId) next.nodeStatuses = { ...state.nodeStatuses, [event.nodeId]: event.payload?.status === 'warning' ? 'warning' : 'completed' }; next.currentNode = event.nodeId ?? ''; break;
    case 'node_failed':
      if (event.nodeId) next.nodeStatuses = { ...state.nodeStatuses, [event.nodeId]: 'failed' }; next.phase = 'running'; next.running = false; break;
    case 'edge_transfer': {
      const edgeId = `${event.sourceNodeId}-${event.targetNodeId}`;
      next.edgeStatuses = { ...state.edgeStatuses, [edgeId]: 'active' }; next.activeEdgeIds = [edgeId]; break;
    }
    case 'tool_called': case 'tool_completed': break;
    case 'critic_failed':
      next.criticResult = 'failed'; next.phase = 'running'; next.running = true; if (event.nodeId) next.nodeStatuses = { ...state.nodeStatuses, [event.nodeId]: 'failed' }; break;
    case 'run_completed':
      next.phase = 'complete'; next.running = false; next.currentNode = ''; break;
  }
  return next;
}

export function reduceArchitectureEvents(events: ArchitectureEvent[], nodeIds: string[], runId: string): ArchitectureEventState {
  return events.reduce(reduceArchitectureEvent, { ...createInitialArchitectureEventState(runId), nodeStatuses: Object.fromEntries(nodeIds.map((id) => [id, 'idle'] as const)) });
}
