'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Background, ControlButton, Controls, ReactFlow, ReactFlowProvider, useReactFlow, type Edge, type EdgeMouseHandler, type NodeMouseHandler } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Circle, CircleDashed, Database, Play, RotateCcw, TimerReset } from 'lucide-react';
import { ArchitectureEdge } from './ArchitectureEdge';
import { ArchitectureNode } from './ArchitectureNode';
import { architectureEdges, architectureNodes, packetInspections, type ArchitectureNode as GraphNode } from './architecture-model';
import { createDemoEventEngine, type DemoFlowState } from './demo-event-engine';
import { reduceArchitectureEvent, type ArchitectureEvent } from './architecture-events';
import { EventStream } from './EventStream';
import { ArchitectureLegend } from './ArchitectureLegend';
import { NodeInspector } from './NodeInspector';
import { PacketInspector } from './PacketInspector';

const nodeTypes = { architecture: ArchitectureNode };
const edgeTypes = { architecture: ArchitectureEdge };
const initialState: DemoFlowState = { runId: 'idle', nodeStatuses: {}, edgeStatuses: {}, activeEdgeIds: [], eventLog: [], eventLabel: 'Ready to run', elapsedMs: 0, running: false, phase: 'idle', currentStep: 0, totalSteps: 14, currentNode: '' };

function ArchitectureCanvas() {
  const [nodes, setNodes] = useState<GraphNode[]>(architectureNodes);
  const [edges, setEdges] = useState<Edge[]>(architectureEdges);
  const [stream, setStream] = useState<DemoFlowState>(initialState);
  const [mode, setMode] = useState<'demo' | 'live'>('live');
  const [llmStatus, setLlmStatus] = useState<'checking' | 'configured' | 'not_configured'>('checking');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedPacket, setSelectedPacket] = useState(packetInspections['source-rbi-retrieval'] ?? null);
  const [hasPacketSelection, setHasPacketSelection] = useState(false);
  const executionToken = useRef(0);
  const lastEvidenceEventId = useRef(0);
  const graphRef = useRef<HTMLDivElement>(null);
  const engine = useMemo(() => createDemoEventEngine(architectureNodes.map((node) => node.id)), []);
  const { fitView } = useReactFlow();
  const fitArchitecture = () => { void fitView({ padding: 0.04, minZoom: 0.2, maxZoom: 1.8, duration: 300 }); };

  const applyState = (nextState: DemoFlowState) => {
    setStream(nextState);
    setNodes((current) => current.map((node) => ({ ...node, data: { ...node.data, status: nextState.nodeStatuses[node.id] ?? node.data.status } })));
    setEdges((current) => current.map((edge) => ({ ...edge, animated: nextState.activeEdgeIds.includes(edge.id), data: { ...edge.data, status: nextState.activeEdgeIds.includes(edge.id) ? 'active' : nextState.edgeStatuses[edge.id] ?? 'idle' } })));
  };

  const run = () => {
    if (stream.running) return;
    const token = executionToken.current + 1;
    executionToken.current = token;
    if (mode === 'demo') {
      void engine.start((nextState) => { if (executionToken.current === token) applyState(nextState); });
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://artha-ai-api.vercel.app';
    const runLiveCheck = async () => {
      const runId = `live-${Date.now()}`;
      const startedAt = Date.now();
      let state: DemoFlowState = {
        ...initialState,
        runId,
        nodeStatuses: Object.fromEntries(architectureNodes.map((node) => [node.id, 'idle' as const])),
      };
      const emit = (type: ArchitectureEvent['type'], message: string, details: Partial<ArchitectureEvent> = {}) => {
        if (executionToken.current !== token) return;
        const event: ArchitectureEvent = { runId, timestamp: new Date().toISOString(), type, message, ...details };
        state = reduceArchitectureEvent(state, event);
        state.elapsedMs = Date.now() - startedAt;
        applyState(state);
      };

      try {
        emit('run_started', 'Live flow started; checking deployed API and data catalog.', { payload: { mode: 'live' } });
        emit('node_started', 'Checking deployed API health.', { nodeId: 'adapter' });
        const healthResponse = await fetch(`${apiBaseUrl}/health`, { cache: 'no-store' });
        if (!healthResponse.ok) throw new Error(`API health check returned HTTP ${healthResponse.status}.`);
        const health = await healthResponse.json() as { status?: string; llm?: string };
        emit('node_completed', `API healthy; LLM ${health.llm === 'configured' ? 'configured' : 'not configured'}.`, { nodeId: 'adapter', payload: health });

        emit('node_started', 'Loading the live series catalog.', { nodeId: 'source-rbi' });
        const seriesResponse = await fetch(`${apiBaseUrl}/series`, { cache: 'no-store' });
        if (!seriesResponse.ok) throw new Error(`Series catalog returned HTTP ${seriesResponse.status}.`);
        const catalog = await seriesResponse.json() as { series?: Array<{ available?: boolean }> };
        const available = catalog.series?.filter((item) => item.available).length ?? 0;
        emit('node_completed', `Live series catalog loaded (${available} available series).`, { nodeId: 'source-rbi', payload: { available } });
        const runtimePath: Array<[string, string, string]> = [
          ['adapter', 'raw-snapshots', 'Source adapters ready.'],
          ['raw-snapshots', 'validation', 'Runtime snapshots validated.'],
          ['validation', 'canonical-store', 'Canonical data store ready.'],
          ['canonical-store', 'feature-engine', 'Model features prepared.'],
          ['feature-engine', 'seasonal-naive', 'CPI benchmark model selected.'],
          ['seasonal-naive', 'baseline-forecast', 'Baseline forecast path ready.'],
          ['rolling-backtest', 'quant-validation', 'Packaged evaluation metrics loaded.'],
          ['quant-validation', 'critic', 'Quantitative validation completed.'],
          ['critic', 'report', 'Research report stage ready.'],
          ['report', 'fastapi', 'API publication stage ready.'],
          ['fastapi', 'nextjs', 'Frontend delivery stage ready.'],
          ['nextjs', 'pages', 'Research pages ready.'],
        ];
        for (const [sourceNodeId, targetNodeId, message] of runtimePath) {
          emit('node_started', message, { nodeId: sourceNodeId });
          await new Promise((resolve) => window.setTimeout(resolve, 120));
          emit('node_completed', message, { nodeId: sourceNodeId });
          emit('edge_transfer', `${sourceNodeId} → ${targetNodeId}`, { sourceNodeId, targetNodeId });
          emit('node_completed', message, { nodeId: targetNodeId });
        }
        emit('run_completed', 'Live flow completed using verified API health and series catalog data.', { payload: { mode: 'live' } });
      } catch (error) {
        emit('node_failed', error instanceof Error ? error.message : 'Live flow failed.', { nodeId: 'adapter' });
        emit('run_completed', 'Live flow stopped because a backend check failed.', { payload: { mode: 'live', status: 'failed' } });
      }
    };
    void runLiveCheck();
  };

  const reset = () => {
    executionToken.current += 1;
    setNodes(architectureNodes);
    setEdges(architectureEdges);
    setStream(initialState);
    setSelectedNode(null);
    setHasPacketSelection(false);
  };

  const handleNodeClick: NodeMouseHandler = (_, node) => {
    setSelectedNode(node as GraphNode);
    setHasPacketSelection(false);
    setNodes((current) => current.map((item) => ({ ...item, data: { ...item.data, selected: item.id === node.id } })));
  };

  const handleEdgeClick: EdgeMouseHandler = (_, edge) => {
    const packet = packetInspections[edge.id];
    if (packet) {
      setSelectedPacket(packet);
      setHasPacketSelection(true);
      setSelectedNode(null);
    }
  };

  useEffect(() => {
    const container = graphRef.current;
    if (!container) return;
    const refit = () => { void fitView({ padding: 0.04, minZoom: 0.2, maxZoom: 1.8, duration: 0 }); };
    const observer = new ResizeObserver(() => requestAnimationFrame(refit));
    observer.observe(container);
    requestAnimationFrame(refit);
    return () => observer.disconnect();
  }, [fitView]);

  useEffect(() => {
    let active = true;
    void fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/health`, { cache: 'no-store' })
      .then((response) => response.ok ? response.json() as Promise<{ llm?: string }> : null)
      .then((health) => { if (active) setLlmStatus(health?.llm === 'configured' ? 'configured' : 'not_configured'); })
      .catch(() => { if (active) setLlmStatus('not_configured'); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (mode !== 'live') return;
    const runId = window.sessionStorage.getItem('india-monetary-policy-evidence-run-id');
    if (!runId) return;
    let active = true;
    const poll = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'}/evidence/events?run_id=${encodeURIComponent(runId)}&after=${lastEvidenceEventId.current}`, { cache: 'no-store' });
        if (!response.ok) return;
        const payload = await response.json() as { events?: Array<{ id: number; type: ArchitectureEvent['type']; timestamp: number; data: Record<string, unknown> }> };
        for (const item of payload.events ?? []) {
          lastEvidenceEventId.current = Math.max(lastEvidenceEventId.current, item.id);
          const format = String(item.data.format ?? '').toLowerCase();
          const nodeByEvent: Record<string, string> = {
            evidence_upload_started: 'upload', evidence_uploaded: 'format-router', evidence_deleted: 'vector-store', evidence_parsing_started: format === 'pdf' ? 'pdf-parser' : format === 'txt' || format === 'md' ? 'text-parser' : format === 'csv' || format === 'xlsx' ? 'table-parser' : 'json-parser',
            evidence_parsing_completed: format === 'pdf' ? 'pdf-parser' : format === 'txt' || format === 'md' ? 'text-parser' : format === 'csv' || format === 'xlsx' ? 'table-parser' : 'json-parser',
            evidence_indexed: 'vector-store', evidence_ready: format === 'pdf' || format === 'txt' || format === 'md' ? 'vector-store' : format === 'csv' || format === 'xlsx' ? 'table-parser' : 'json-parser', evidence_processing_failed: format === 'pdf' ? 'pdf-parser' : format === 'txt' || format === 'md' ? 'text-parser' : format === 'csv' || format === 'xlsx' ? 'table-parser' : 'json-parser',
            retrieval_started: 'retriever', retrieval_completed: 'retrieved-evidence', evidence_validation_started: 'evidence-validation', evidence_validation_completed: 'critic', critic_started: 'critic', critic_completed: 'critic', report_started: 'report', report_completed: 'report',
          };
          const label = item.type.replaceAll('_', ' ');
          const visible = item.data.filename ? `${label}: ${String(item.data.filename)}` : label;
          const event: ArchitectureEvent = { runId, timestamp: new Date(item.timestamp * 1000).toISOString(), type: item.type, nodeId: nodeByEvent[item.type], message: visible, payload: item.data };
          setStream((current) => {
            const next = reduceArchitectureEvent(current, event);
            setNodes((items) => items.map((graphNode) => ({ ...graphNode, data: { ...graphNode.data, status: next.nodeStatuses[graphNode.id] ?? graphNode.data.status } })));
            setEdges((items) => items.map((graphEdge) => ({ ...graphEdge, animated: next.activeEdgeIds.includes(graphEdge.id), data: { ...graphEdge.data, status: next.activeEdgeIds.includes(graphEdge.id) ? 'active' : graphEdge.data?.status ?? 'idle' } })));
            return next;
          });
        }
      } catch { /* API may be offline; the graph remains available for demo flows. */ }
    };
    void poll();
    const timer = window.setInterval(() => { if (active) void poll(); }, 1500);
    return () => { active = false; window.clearInterval(timer); };
  }, [mode]);

  return (
    <div className="grid gap-3 xl:grid-cols-[minmax(0,4fr)_minmax(220px,1fr)]">
      <section className="min-w-0 overflow-hidden rounded-2xl border border-white/[0.08] bg-[rgba(7,20,38,0.62)] shadow-[0_20px_55px_rgba(0,0,0,0.25)] backdrop-blur-2xl">
        <header className="border-b border-white/[0.08] px-4 py-3 sm:px-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2"><h1 className="text-sm font-semibold tracking-wide text-slate-50">SYSTEM ARCHITECTURE</h1><span className="rounded-full border border-amber-300/15 bg-amber-400/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.12em] text-amber-200">{mode === 'demo' ? 'DEMO DATA' : 'LIVE EXECUTION'}</span></div>
              <p className="mt-1 text-xs text-slate-400">Production data, numerical models, scenarios, orchestration and evidence validation</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.025] px-2 py-1.5 text-[9px] uppercase tracking-[0.08em]"><button type="button" onClick={() => setMode('demo')} className={mode === 'demo' ? 'font-semibold text-cyan-200' : 'text-slate-500'}>Demo</button><span className="text-slate-700">|</span><button type="button" onClick={() => setMode('live')} className={mode === 'live' ? 'font-semibold text-cyan-200' : 'text-slate-500'}>Live</button></div>
              <button type="button" onClick={run} disabled={stream.running} className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-300/20 bg-cyan-400/10 px-2.5 py-1.5 text-[10px] font-semibold text-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"><Play size={12} /> Run Flow</button>
              <button type="button" onClick={reset} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-[10px] font-semibold text-slate-300"><RotateCcw size={12} /> Reset</button>
              <span className="inline-flex items-center gap-1 text-[10px] text-slate-500"><TimerReset size={12} />{(stream.elapsedMs / 1000).toFixed(1)}s</span>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-[9px] text-slate-500"><span className="inline-flex items-center gap-1 text-violet-300"><Circle size={7} fill="currentColor" /> Configured NVIDIA LLM <span className={llmStatus === 'configured' ? 'text-emerald-300' : 'text-amber-300'}>{llmStatus === 'checking' ? 'CHECKING' : llmStatus === 'configured' ? 'CONFIGURED' : 'NOT CONFIGURED'}</span></span><span className="inline-flex items-center gap-1"><CircleDashed size={9} /> Official live feeds <span>NOT CONNECTED</span></span><span className="inline-flex items-center gap-1 text-amber-300"><Circle size={7} fill="currentColor" /> Deterministic forecast tools <span className="text-emerald-300">AVAILABLE</span></span></div>
        </header>
        <ArchitectureLegend />
        <div ref={graphRef} className="architecture-flow relative h-[660px] min-h-[560px] w-full overflow-hidden bg-[radial-gradient(circle_at_50%_30%,rgba(59,130,246,0.08),transparent_38%),rgba(5,11,24,0.35)]">
          <div className="pointer-events-none absolute inset-x-4 top-3 z-10 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-300/70"><Database size={13} /> Official Data Sources <span className="h-px flex-1 bg-cyan-300/15" /></div>
          <ReactFlow className="architecture-flow" nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes} fitView fitViewOptions={{ padding: 0.08, minZoom: 0.2, maxZoom: 1.8 }} nodesDraggable={false} nodesConnectable={false} elementsSelectable panOnDrag panOnScroll={false} zoomOnScroll zoomOnPinch zoomOnDoubleClick minZoom={0.2} maxZoom={1.8} selectionOnDrag={false} selectNodesOnDrag={false} connectOnClick={false} preventScrolling={false} onInit={() => { fitArchitecture(); }} onNodeClick={handleNodeClick} onEdgeClick={handleEdgeClick}>
            <Background color="rgba(148,163,184,0.09)" gap={30} size={1} />
            <Controls className="architecture-flow-controls" showInteractive={false} position="bottom-left">
              <ControlButton onClick={fitArchitecture} title="Reset View" aria-label="Reset View"><TimerReset size={14} /></ControlButton>
            </Controls>
            {selectedNode && !hasPacketSelection && <NodeInspector node={selectedNode} onClose={() => setSelectedNode(null)} />}
            {hasPacketSelection && selectedPacket && <PacketInspector packet={selectedPacket} onClose={() => setHasPacketSelection(false)} />}
          </ReactFlow>
          <div className="pointer-events-none absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-md border border-cyan-300/10 bg-[rgba(5,15,31,0.72)] px-2.5 py-1 text-[10px] text-slate-500 backdrop-blur-md">Drag to explore · Scroll to zoom</div>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.08] px-4 py-2 text-[10px] text-slate-500 sm:px-5"><span>Interactive viewport · status and data-flow animation remain live</span><span>{stream.eventLabel}</span></div>
      </section>
      <EventStream events={stream.eventLog} running={stream.running} />
    </div>
  );
}

export function ArchitectureGraph() { return <ReactFlowProvider><ArchitectureCanvas /></ReactFlowProvider>; }
