'use client';

import {
  PageHeaderSkeleton,
  ChartSkeleton,
  SkeletonCard,
  SkeletonCardHeader,
  SkeletonCardContent,
  Skeleton,
} from './index';

export function ForecastsSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      {/* Page Header */}
      <PageHeaderSkeleton wide />

      {/* Mock Data Notice */}
      <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.07] flex items-start gap-3 p-4">
        <Skeleton variant="circular" width={16} height={16} className="mt-0.5 shrink-0" />
        <div className="space-y-1 flex-1">
          <Skeleton variant="text" width="100" height={10} />
          <Skeleton variant="text" width="250" height={8} />
        </div>
      </SkeletonCard>

      {/* Main Chart Section */}
      <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <ChartSkeleton height={350} headerBadge footerItems={3} />

        {/* Baseline Benchmark */}
        <SkeletonCard>
          <SkeletonCardHeader showIcon={true} showBadge={false} />
          <SkeletonCardContent>
            <div className="mt-4 grid grid-cols-4 gap-2" aria-hidden="true">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} variant="text" width="100%" height={32} borderRadius="xl" />
              ))}
            </div>
            <div className="mt-5 space-y-3" aria-hidden="true">
              <Skeleton variant="text" width="80%" height={10} />
              <div className="grid grid-cols-3 gap-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <SkeletonCard key={index} variant="outlined" className="p-3">
                    <Skeleton variant="text" width="60%" height={8} />
                    <Skeleton variant="text" width="40%" height={20} className="mt-1 font-semibold" />
                    <Skeleton variant="text" width="50%" height={8} className="mt-1" />
                  </SkeletonCard>
                ))}
              </div>
              <Skeleton variant="text" width="80%" height={10} className="mt-3" />
            </div>
          </SkeletonCardContent>
        </SkeletonCard>
      </div>

      {/* Rolling-origin Backtest */}
      <SkeletonCard>
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5" aria-hidden="true">
            {Array.from({ length: 5 }).map((_, index) => (
              <SkeletonCard key={index} variant="outlined" className="p-3">
                <Skeleton variant="text" width="60%" height={8} className="uppercase tracking-[0.12em]" />
                <Skeleton variant="text" width="50%" height={16} className="mt-1 font-semibold" />
              </SkeletonCard>
            ))}
          </div>
          <Skeleton variant="text" width="80%" height={10} className="mt-3" />
        </SkeletonCardContent>
      </SkeletonCard>
    </div>
  );
}