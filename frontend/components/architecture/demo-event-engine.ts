import type { ArchitectureStatus } from './architecture-model';
import { createInitialArchitectureEventState, reduceArchitectureEvent, type ArchitectureEvent, type ArchitectureEventState, type ArchitectureEventType } from './architecture-events';

export type DemoScenario = 'success';
export type { ArchitectureEventLogEntry as OperationalEvent } from './architecture-events';
export type { ArchitectureEventState as DemoFlowState } from './architecture-events';
export type EventCategory = 'data' | 'agents' | 'tools' | 'policy' | 'errors';
export type DemoFlowListener = (state: ArchitectureEventState) => void;
export function createDemoEventEngine(nodeIds: string[]) {
  return {
    async start(listener: DemoFlowListener) {
      const runId = `demo-${Date.now()}`;
      const startedAt = Date.now();
      let state: ArchitectureEventState = { ...createInitialArchitectureEventState(runId), nodeStatuses: Object.fromEntries(nodeIds.map((id) => [id, 'idle' as ArchitectureStatus])) };
      const emit = (type: ArchitectureEventType, message: string, details: Partial<ArchitectureEvent> = {}) => {
        const event: ArchitectureEvent = { runId, timestamp: new Date().toISOString(), type, message, ...details };
        state = reduceArchitectureEvent(state, event); state.elapsedMs = Date.now() - startedAt; listener(state);
      };
      const path: Array<[string, string, string, string]> = [
        ['adapter', 'raw-snapshots', 'Source adapters captured the configured runtime inputs.', 'adapter-raw'],
        ['raw-snapshots', 'validation', 'Validated snapshot structure and provenance metadata.', 'raw-validation'],
        ['validation', 'canonical-store', 'Published validated observations to the canonical store.', 'validation-canonical'],
        ['canonical-store', 'feature-engine', 'Prepared model-ready features without mixing series bases.', 'canonical-feature'],
        ['feature-engine', 'seasonal-naive', 'Loaded the connected CPI benchmark model.', 'feature-seasonal-naive'],
        ['seasonal-naive', 'baseline-forecast', 'Generated the deterministic baseline forecast.', 'seasonal-naive-baseline'],
        ['rolling-backtest', 'quant-validation', 'Loaded packaged evaluation metrics and interval coverage.', 'eval-roll'],
        ['quant-validation', 'critic', 'Passed numerical output to validation.', 'quant-critic'],
        ['critic', 'report', 'Assembled cited runtime findings.', 'critic-report'],
        ['report', 'fastapi', 'Published the research result through FastAPI.', 'report-api'],
        ['fastapi', 'nextjs', 'Delivered the API response to the research terminal.', 'api-ui'],
        ['nextjs', 'pages', 'Updated the connected research pages.', 'ui-pages'],
      ];
      emit('run_started', 'Runtime architecture flow started.', { payload: { mode: 'runtime_preview' } });
      for (const [sourceNodeId, targetNodeId, message, edgeId] of path) {
        emit('node_started', message, { nodeId: sourceNodeId });
        await new Promise((resolve) => window.setTimeout(resolve, 220));
        emit('node_completed', message, { nodeId: sourceNodeId });
        emit('edge_transfer', `${sourceNodeId} → ${targetNodeId}`, { sourceNodeId, targetNodeId, payload: { edgeId } });
        emit('node_started', message, { nodeId: targetNodeId });
        await new Promise((resolve) => window.setTimeout(resolve, 180));
        emit('node_completed', message, { nodeId: targetNodeId });
      }
      emit('run_completed', 'Runtime-aligned flow completed. Preview events represent the connected execution path; they do not claim a new model run.', { payload: { status: 'completed' }, durationMs: Date.now() - startedAt });
    },
  };
}

export function getNodeStatusLabel(status: ArchitectureStatus) { return status.toUpperCase(); }
