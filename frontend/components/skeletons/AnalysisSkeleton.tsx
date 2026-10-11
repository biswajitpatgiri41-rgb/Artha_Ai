'use client';

import {
  PageHeaderSkeleton,
  KPIGridSkeleton,
  ChartSkeleton,
  DonutChartSkeleton,
  SkeletonCard,
  SkeletonCardHeader,
  SkeletonCardContent,
  SkeletonCardFooter,
  Skeleton,
} from './index';

export function AnalysisSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      {/* Page Header */}
      <PageHeaderSkeleton wide />

      {/* Mock Analysis Notice */}
      <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.07] flex items-start gap-3 p-4">
        <Skeleton variant="circular" width={16} height={16} className="mt-0.5 shrink-0" />
        <div className="space-y-1 flex-1">
          <Skeleton variant="text" width="100" height={10} />
          <Skeleton variant="text" width="200" height={8} />
        </div>
      </SkeletonCard>

      {/* KPI Grid */}
      <KPIGridSkeleton count={4} />

      {/* Main Chart Section */}
      <div className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
        <ChartSkeleton height={350} headerBadge footerItems={3} />
        <DonutChartSkeleton size={245} legendItems={3} />
      </div>

      {/* Key Inflation Drivers */}
      <SkeletonCard>
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <SkeletonCard key={index} variant="outlined" className="p-4">
                <div className="flex items-center justify-between gap-2" aria-hidden="true">
                  <Skeleton variant="text" width="60%" height={14} />
                  <Skeleton variant="text" width={80} height={20} borderRadius="9999px" />
                </div>
                <Skeleton variant="text" width="90%" height={10} className="mt-2" />
                <Skeleton variant="text" width="60%" height={16} className="mt-3 font-semibold" />
                <Skeleton variant="text" width="80%" height={10} className="mt-1" />
                <Skeleton variant="rectangular" width="100%" height={6} borderRadius="9999px" className="mt-3" />
              </SkeletonCard>
            ))}
          </div>
        </SkeletonCardContent>
      </SkeletonCard>

      {/* Unavailable Model Status */}
      <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.06] p-3 text-xs">
        <div className="flex items-start gap-3" aria-hidden="true">
          <Skeleton variant="circular" width={18} height={18} className="shrink-0" />
          <div className="space-y-1 flex-1">
            <Skeleton variant="text" width="140" height={10} />
            <Skeleton variant="text" width="200" height={10} />
          </div>
        </div>
      </SkeletonCard>

      {/* Evidence & Sources */}
      <SkeletonCard>
        <SkeletonCardHeader showIcon={true} showBadge={false} />
        <SkeletonCardContent>
          <div className="mt-4 flex flex-wrap gap-2" aria-hidden="true">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} variant="text" width={160} height={24} borderRadius="9999px" />
            ))}
          </div>
        </SkeletonCardContent>
      </SkeletonCard>
    </div>
  );
}