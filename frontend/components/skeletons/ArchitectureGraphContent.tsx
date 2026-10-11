'use client';

import { Skeleton } from './index';

export function ArchitectureGraphContent() {
  return (
    <div className="relative" aria-hidden="true">
      <ControlsHeaderSkeleton />
      <GraphAreaSkeleton />
      <FooterSkeleton />
    </div>
  );
}

function ControlsHeaderSkeleton() {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-4">
      <div className="flex flex-wrap items-center gap-3">
        <Skeleton variant="text" width="100" height={10} className="uppercase tracking-[0.18em]" />
        <div className="flex items-center gap-2 text-[9px]">
          <Skeleton variant="circular" width={7} height={7} />
          <Skeleton variant="text" width="100" height={8} />
          <Skeleton variant="text" width="80" height={8} />
          <Skeleton variant="text" width="100" height={8} />
          <Skeleton variant="text" width="100" height={8} />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Skeleton variant="text" width={100} height={40} borderRadius="lg" />
        <Skeleton variant="text" width={80} height={40} borderRadius="lg" />
        <Skeleton variant="text" width={100} height={24} />
      </div>
    </div>
  );
}

function GraphAreaSkeleton() {
  return (
    <div className="relative h-[660px] min-h-[560px] w-full overflow-hidden bg-[radial-gradient(circle_at_50%_30%,rgba(59,130,246,0.08),transparent_38%),rgba(5,15,31,0.35)] rounded-xl">
      {/* Layer labels */}
      <div className="pointer-events-none absolute inset-x-4 top-3 z-10 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-300/70">
        <Skeleton variant="circular" width={13} height={13} />
        <Skeleton variant="text" width="160" height={10} />
        <Skeleton variant="text" width={200} height={10} className="h-px flex-1 bg-sky-300/15" />
      </div>

      {/* Graph rows - simulating the architecture layout */}
      <div className="absolute inset-0 flex flex-col justify-between px-8 py-12">
        {/* Row 1: Data Sources */}
        <div className="flex items-center justify-between">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonNode key={`source-${i}`} width={145} height={68} />
          ))}
        </div>

        {/* Row 2: Tools */}
        <div className="flex items-center justify-between">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonNode key={`tool-${i}`} width={210} height={96} />
          ))}
        </div>

        {/* Row 3: Orchestrator */}
        <div className="flex items-center justify-center">
          <SkeletonNode width={210} height={96} />
        </div>

        {/* Row 4: Agents */}
        <div className="flex items-center justify-between">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonNode key={`agent-${i}`} width={210} height={96} />
          ))}
        </div>

        {/* Row 5: Forecast/Scenario */}
        <div className="flex items-center justify-between">
          {Array.from({ length: 2 }).map((_, i) => (
            <SkeletonNode key={`forecast-${i}`} width={210} height={96} />
          ))}
        </div>

        {/* Row 6: Reports/Output */}
        <div className="flex items-center justify-center">
          <SkeletonNode width={210} height={96} />
        </div>
      </div>

      {/* Placeholder edges - subtle lines */}
      <div className="pointer-events-none absolute inset-0">
        <svg className="w-full h-full" style={{ opacity: 0.15 }}>
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L0,6 L8,3 Z" fill="currentColor" />
            </marker>
          </defs>
          {Array.from({ length: 5 }).map((_, row) => (
            <g key={`edges-${row}`}>
              {Array.from({ length: 4 }).map((_, i) => (
                <line
                  key={i}
                  x1={`${20 + i * 24}%`}
                  y1={`${15 + row * 16}%`}
                  x2={`${20 + i * 24}%`}
                  y2={`${28 + row * 16}%`}
                  stroke="currentColor"
                  strokeWidth="1"
                  strokeDasharray="4,4"
                  markerEnd="url(#arrowhead)"
                />
              ))}
            </g>
          ))}
        </svg>
      </div>

      {/* Bottom hint */}
      <div className="pointer-events-none absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-md border border-cyan-300/10 bg-[rgba(5,15,31,0.72)] px-2.5 py-1 text-[10px] text-slate-500 backdrop-blur-md">
        <Skeleton variant="text" width="200" height={10} />
      </div>
    </div>
  );
}

function FooterSkeleton() {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.08] px-4 py-2 text-[10px]">
      <Skeleton variant="text" width="250" height={10} />
      <Skeleton variant="text" width="150" height={10} />
    </div>
  );
}

function SkeletonNode({ width = 210, height = 96 }: { width?: number; height?: number }) {
  return (
    <div className="group relative" style={{ width, height }} aria-hidden="true">
      <div className="absolute inset-x-4 top-0 h-px bg-sky-400/45 opacity-80" />
      <div className="absolute inset-0 rounded-2xl border border-sky-400/45 bg-[rgba(8,15,30,0.88)] backdrop-blur-xl shadow-[0_0_20px_rgba(14,165,233,0.10)]">
        <div className="p-4 h-full">
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <Skeleton variant="circular" width={18} height={18} />
              <Skeleton variant="text" width="80%" height={15} />
            </div>
            <Skeleton variant="circular" width={8} height={8} />
          </div>
          <Skeleton variant="text" width="90%" height={11} className="mt-3" />
          <div className="mt-3 flex items-center border-t border-white/[0.08] pt-2">
            <Skeleton variant="text" width="100" height={10} />
          </div>
        </div>
      </div>
    </div>
  );
}
