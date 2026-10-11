'use client';

import { Skeleton, SkeletonCard, SkeletonCardHeader, SkeletonCardContent } from './index';

export function ScenarioLabSkeleton() {
  return (
    <SkeletonCard
      variant="elevated"
      className="relative overflow-hidden border-amber-300/15 bg-[rgba(15,23,42,0.66)] shadow-[0_20px_55px_rgba(0,0,0,0.25),0_0_30px_rgba(245,158,11,0.045)]"
    >
      <SkeletonCardHeader showIcon showBadge />
      <SkeletonCardContent>
        <div className="relative mt-5 grid gap-x-5 gap-y-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="block" aria-hidden="true">
              <div className="flex items-center justify-between gap-2 text-[11px]">
                <Skeleton variant="text" width="70%" height={11} />
                <Skeleton variant="text" width="40%" height={14} />
              </div>
              <Skeleton variant="rectangular" width="100%" height={24} className="mt-3" borderRadius="8px" />
            </div>
          ))}
        </div>
        <div className="relative mt-5 flex flex-wrap items-center gap-3">
          <Skeleton variant="rectangular" width={120} height={40} borderRadius="xl" />
          <Skeleton variant="text" width={200} height={10} />
        </div>
        <div className="relative mt-5 border-t border-white/[0.07] pt-4">
          <Skeleton variant="text" width="120" height={10} className="uppercase tracking-[0.16em]" />
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <SkeletonCard key={index} variant="outlined" className="px-3 py-2" padding="px-3 py-2">
                <div className="space-y-1" aria-hidden="true">
                  <Skeleton variant="text" width="60%" height={8} />
                  <Skeleton variant="text" width="40%" height={14} />
                </div>
              </SkeletonCard>
            ))}
          </div>
        </div>
      </SkeletonCardContent>
    </SkeletonCard>
  );
}