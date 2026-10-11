'use client';

import { SkeletonCard, SkeletonCardHeader, SkeletonCardContent, Skeleton } from './index';

export function LowerSectionSkeleton() {
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_1.1fr]" aria-hidden="true">
      <SkeletonCard variant="outlined" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index}>
                <div className="flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <Skeleton variant="circular" width={14} height={14} />
                    <Skeleton variant="text" width="80%" height={10} />
                  </div>
                  <Skeleton variant="text" width="30" height={12} />
                </div>
                <Skeleton variant="rectangular" width="100%" height={6} borderRadius="9999px" className="mt-2" />
              </div>
            ))}
          </div>
        </SkeletonCardContent>
      </SkeletonCard>
      <SkeletonCard variant="outlined" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                <Skeleton variant="text" width="60%" height={8} />
                <Skeleton variant="text" width="40%" height={10} className="font-semibold" />
              </div>
            ))}
          </div>
          <div className="mt-5">
            <Skeleton variant="rectangular" width="100%" height={8} borderRadius="9999px" />
          </div>
        </SkeletonCardContent>
      </SkeletonCard>
    </div>
  );
}