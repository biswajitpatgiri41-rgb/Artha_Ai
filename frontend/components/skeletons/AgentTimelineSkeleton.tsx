'use client';

import { Skeleton, SkeletonCard } from './index';

export function AgentTimelineSkeleton() {
  return (
    <SkeletonCard className="rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.68)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.24)] backdrop-blur-2xl">
      <div className="flex items-start justify-between" aria-hidden="true">
        <div className="space-y-1">
          <Skeleton variant="text" width="180" height={16} />
          <Skeleton variant="text" width="280" height={10} />
        </div>
        <div className="flex items-center gap-1.5">
          <Skeleton variant="circular" width={6} height={6} />
          <Skeleton variant="text" width="60" height={10} />
        </div>
      </div>
      <div className="mt-5 space-y-3">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="flex gap-3" aria-hidden="true">
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
    </SkeletonCard>
  );
}