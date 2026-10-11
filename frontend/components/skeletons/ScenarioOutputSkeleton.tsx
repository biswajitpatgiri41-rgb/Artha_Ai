'use client';

import { SkeletonCard, SkeletonCardHeader, SkeletonCardContent, Skeleton } from './index';

export function ScenarioOutputSkeleton() {
  return (
    <SkeletonCard variant="elevated" className="relative overflow-hidden border-blue-300/15 bg-[rgba(15,23,42,0.66)] shadow-[0_20px_55px_rgba(0,0,0,0.25),0_0_30px_rgba(59,130,246,0.045)]">
      <SkeletonCardHeader showIcon={true} showBadge={true} />
      <SkeletonCardContent>
        <div className="mt-6 grid gap-3 sm:grid-cols-3" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <SkeletonCard key={index} variant="outlined" className="border-slate-200 bg-white p-4 shadow-sm">
              <Skeleton variant="text" width="80%" height={8} className="uppercase tracking-[0.12em]" />
              <div className="mt-3 flex items-end gap-2">
                <Skeleton variant="text" width="80" height={32} className="font-semibold" />
                <Skeleton variant="text" width="70" height={10} />
              </div>
              <Skeleton variant="text" width="80%" height={8} className="mt-2" />
            </SkeletonCard>
          ))}
        </div>
        <SkeletonCard variant="outlined" className="mt-5 rounded-lg bg-slate-50 p-4">
          <div className="flex items-center justify-between" aria-hidden="true">
            <div>
              <Skeleton variant="text" width="120" height={10} />
              <Skeleton variant="text" width="180" height={8} className="mt-1" />
            </div>
            <Skeleton variant="text" width={60} height={10} />
          </div>
          <div className="mt-5 flex h-28 items-end justify-between gap-2" aria-hidden="true">
            {Array.from({ length: 12 }).map((_, index) => (
              <div key={index} className="flex flex-1 flex-col items-center gap-2">
                <Skeleton variant="rectangular" width="100%" height={60} borderRadius="4px 4px 0 0" className="w-full" />
                <Skeleton variant="text" width="100%" height={8} />
              </div>
            ))}
          </div>
          <Skeleton variant="text" width="90%" height={8} className="mt-3" />
        </SkeletonCard>
        <SkeletonCard variant="outlined" className="mt-5 flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50/60 p-3">
          <Skeleton variant="circular" width={15} height={15} className="mt-0.5 shrink-0" />
          <div className="space-y-1 flex-1" aria-hidden="true">
            <Skeleton variant="text" width="100%" height={10} />
            <Skeleton variant="text" width="80%" height={10} />
          </div>
        </SkeletonCard>
      </SkeletonCardContent>
    </SkeletonCard>
  );
}