import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, type Edge, type EdgeProps } from '@xyflow/react';

interface ArchitectureEdgeData extends Record<string, unknown> { color?: string; }

export function ArchitectureEdge({ id, sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, data, animated, label }: EdgeProps<Edge<ArchitectureEdgeData>>) {
  const [path] = getSmoothStepPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, borderRadius: 12, offset: 18 });
  const color = data?.color ?? '#22d3ee';
  return <>
    <BaseEdge id={id} path={path} style={{ cursor: 'default', stroke: animated ? color : 'rgba(100,116,139,0.40)', strokeWidth: animated ? 2.5 : 1.5, filter: animated ? `drop-shadow(0 0 5px ${color})` : undefined }} />
    {animated && <circle r="3.2" fill={color} style={{ filter: `drop-shadow(0 0 4px ${color})` }}><animateMotion dur="900ms" repeatCount="1" path={path} /></circle>}
    {label && <EdgeLabelRenderer><span className="nodrag nopan rounded bg-[#071426]/90 px-1.5 py-0.5 text-[9px] text-slate-400">{label}</span></EdgeLabelRenderer>}
  </>;
}
