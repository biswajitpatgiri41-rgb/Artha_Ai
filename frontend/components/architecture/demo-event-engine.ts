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
      emit('run_started', 'Architecture preview started; demo mode does not execute research modules.', { payload: { mode: 'preview_only' } });
      emit('tool_called', 'Source connectivity and model execution are not verified by this preview.', { nodeId: 'System', payload: { mode: 'preview_only' } });
      emit('tool_completed', 'Preview ended without marking agents, models, or scenarios completed.', { nodeId: 'System', durationMs: Date.now() - startedAt, payload: { status: 'not_executed' } });
      emit('run_completed', 'Preview complete; no operational execution was simulated.', { payload: { status: 'preview_only' } });
    },
  };
}

export function getNodeStatusLabel(status: ArchitectureStatus) { return status.toUpperCase(); }
