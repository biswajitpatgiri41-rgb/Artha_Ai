'use client';

import { Skeleton, SkeletonCard, SkeletonCardHeader, SkeletonCardContent } from './index';

export function PolicyIntelligenceSkeleton() {
  return (
    <SkeletonCard
      variant="elevated"
      className="relative overflow-hidden border-violet-300/15 bg-[rgba(15,23,42,0.66)] shadow-[0_20px_55px_rgba(0,0,0,0.25),0_0_30px_rgba(139,92,246,0.06)]"
    >
      <SkeletonCardHeader showIcon={true} showBadge={false} />
      <SkeletonCardContent>
        <Skeleton variant="text" width="120" height={10} className="uppercase tracking-[0.16em]" />
        <Skeleton variant="text" width="60%" height={28} className="mt-2" />
        <div className="mt-4 max-w-xs">
          <div className="mb-2 flex items-center justify-between text-xs">
            <Skeleton variant="text" width="60" height={10} />
            <Skeleton variant="text" width="40" height={12} />
          </div>
          <Skeleton variant="rectangular" width="100%" height={8} borderRadius="9999px" />
        </div>
        <div className="relative mt-5 flex flex-wrap gap-2">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} variant="text" width={80} height={24} borderRadius="9999px" />
          ))}
        </div>
        <SkeletonCard variant="outlined" className="mt-5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3">
          <div className="space-y-4" aria-hidden="true">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index}>
                <div className="flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <Skeleton variant="circular" width={14} height={14} />
                    <Skeleton variant="text" width="100" height={10} />
                  </div>
                  <Skeleton variant="text" width="30" height={12} />
                </div>
                <Skeleton variant="rectangular" width="100%" height={6} borderRadius="9999px" className="mt-2" />
              </div>
            ))}
          </div>
        </SkeletonCard>
        <Skeleton variant="text" width={140} height={12} className="relative mt-4" />
        <Skeleton variant="text" width="80%" height={10} className="relative mt-5 border-t border-white/[0.07] pt-3" />
      </SkeletonCardContent>
    </SkeletonCard>
  );
}