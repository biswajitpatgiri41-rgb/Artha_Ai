'use client';

import {
  PageHeaderSkeleton,
  SkeletonCard,
  SkeletonCardHeader,
  SkeletonCardContent,
  Skeleton,
} from './index';

export function LogsSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      <PageHeaderSkeleton wide />

      {/* Mock Agent Events Notice */}
      <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.07] flex items-start gap-3 p-4">
        <Skeleton variant="circular" width={17} height={17} className="mt-0.5 shrink-0" />
        <div className="space-y-1 flex-1">
          <Skeleton variant="text" width="100" height={10} />
          <Skeleton variant="text" width="250" height={8} />
        </div>
      </SkeletonCard>

      {/* Unavailable Agent Status */}
      <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.06] p-3 max-w-xl">
        <div className="flex items-start gap-3" aria-hidden="true">
          <Skeleton variant="circular" width={18} height={18} className="shrink-0" />
          <div className="space-y-1 flex-1">
            <Skeleton variant="text" width="140" height={10} />
            <Skeleton variant="text" width="200" height={10} />
          </div>
        </div>
      </SkeletonCard>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3" aria-hidden="true">
        {Array.from({ length: 3 }).map((_, index) => (
          <SkeletonCard key={index} variant="outlined" className="border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <Skeleton variant="circular" width={16} height={16} />
              <Skeleton variant="text" width="100" height={10} className="uppercase tracking-[0.12em]" />
            </div>
            <Skeleton variant="text" width="100" height={40} className="mt-3 font-semibold" />
          </SkeletonCard>
        ))}
      </div>

      {/* Execution Order / Research Run Trace */}
      <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <AgentTimelineSkeleton />
        </SkeletonCardContent>
      </SkeletonCard>
    </div>
  );
}

function AgentTimelineSkeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="flex gap-3">
          <div className="relative flex w-5 justify-center">
            {index < 4 && <Skeleton className="absolute top-5 h-full w-px" width={1} height="100%" />}
            <Skeleton variant="circular" width={15} height={15} className="z-10" />
          </div>
          <details className="group min-w-0 flex-1 rounded-xl border border-white/[0.07] bg-white/[0.035] p-3">
            <summary className="flex cursor-pointer list-none items-start justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Skeleton variant="text" width="160" height={10} />
                  <Skeleton variant="text" width="80" height={16} borderRadius="9999px" />
                </div>
                <Skeleton variant="text" width="80%" height={10} />
              </div>
              <Skeleton variant="text" width={14} height={14} />
            </summary>
            <div className="mt-4 grid gap-4 border-t border-white/[0.08] pt-3 text-[10px] sm:grid-cols-2">
              <div className="space-y-2">
                <Skeleton variant="text" width="100" height={10} />
                <Skeleton variant="text" width="180" height={10} />
                <Skeleton variant="text" width="200" height={10} />
              </div>
              <div className="space-y-2">
                <Skeleton variant="text" width="100" height={10} />
                <Skeleton variant="text" width="180" height={10} />
                <Skeleton variant="text" width="200" height={10} />
              </div>
            </div>
          </details>
        </div>
      ))}
    </div>
  );
}