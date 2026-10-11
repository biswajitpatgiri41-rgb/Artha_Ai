'use client';

import {
  PageHeaderSkeleton,
  SkeletonCard,
  SkeletonCardHeader,
  SkeletonCardContent,
  Skeleton,
} from './index';

export function ReportsSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      <PageHeaderSkeleton wide />

      {/* Mock Report Archive Notice */}
      <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.07] flex items-start gap-3 p-4">
        <Skeleton variant="circular" width={17} height={17} className="mt-0.5 shrink-0" />
        <div className="space-y-1 flex-1">
          <Skeleton variant="text" width="100" height={10} />
          <Skeleton variant="text" width="250" height={8} />
        </div>
      </SkeletonCard>

      {/* Research Pipeline Card */}
      <SkeletonCard variant="outlined" className="border-blue-200 bg-white p-5 shadow-sm">
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="space-y-1" aria-hidden="true">
            <Skeleton variant="text" width="160" height={10} className="uppercase tracking-[0.18em]" />
            <Skeleton variant="text" width="250" height={24} />
            <Skeleton variant="text" width="80%" height={16} className="mt-1" />
          </div>
          <SkeletonCard variant="outlined" className="mt-5">
            <div className="space-y-3" aria-hidden="true">
              <Skeleton variant="text" width="100%" height={40} borderRadius="xl" />
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton variant="circular" width={24} height={24} />
                  <div className="flex-1 space-y-1">
                    <Skeleton variant="text" width="80%" height={12} />
                    <Skeleton variant="text" width="60%" height={10} />
                  </div>
                </div>
              ))}
            </div>
          </SkeletonCard>
          <Skeleton variant="text" width={160} height={40} borderRadius="xl" className="mt-5" />
        </SkeletonCardContent>
      </SkeletonCard>

      {/* Search/Filter Controls */}
      <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardContent>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between" aria-hidden="true">
            <Skeleton variant="text" width={320} height={40} borderRadius="xl" />
            <div className="flex items-center gap-2">
              <Skeleton variant="text" width="60" height={10} className="uppercase tracking-[0.1em]" />
              <Skeleton variant="text" width={140} height={40} borderRadius="xl" />
            </div>
            <div className="flex items-center gap-2">
              <Skeleton variant="text" width="40" height={10} className="uppercase tracking-[0.1em]" />
              <Skeleton variant="text" width={120} height={40} borderRadius="xl" />
            </div>
          </div>
        </SkeletonCardContent>
      </SkeletonCard>

      {/* Report Cards/List */}
      <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardContent>
          <div className="space-y-4" aria-hidden="true">
            {Array.from({ length: 5 }).map((_, index) => (
              <ReportCardSkeleton key={index} />
            ))}
          </div>
          <div className="mt-4">
            <Skeleton variant="text" width="200" height={10} className="text-center" />
          </div>
        </SkeletonCardContent>
      </SkeletonCard>
    </div>
  );
}

function ReportCardSkeleton() {
  return (
    <div className="rounded-lg border border-slate-200 p-4" aria-hidden="true">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Skeleton variant="text" width="100" height={16} className="uppercase tracking-[0.12em]" />
          <Skeleton variant="text" width="250" height={20} className="font-semibold" />
          <Skeleton variant="text" width="200" height={10} />
        </div>
        <Skeleton variant="text" width={80} height={24} borderRadius="md" />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3" aria-hidden="true">
        <div className="space-y-1">
          <Skeleton variant="text" width="80" height={10} className="uppercase tracking-[0.1em]" />
          <Skeleton variant="text" width="100" height={16} className="font-mono font-semibold" />
        </div>
        <div className="space-y-1">
          <Skeleton variant="text" width="80" height={10} className="uppercase tracking-[0.1em]" />
          <Skeleton variant="text" width="80" height={12} />
        </div>
        <div className="space-y-1">
          <Skeleton variant="text" width="80" height={10} className="uppercase tracking-[0.1em]" />
          <Skeleton variant="text" width="100" height={12} />
        </div>
      </div>
      <Skeleton variant="rectangular" width="100%" height={8} borderRadius="9999px" className="mt-4" />
      <div className="mt-4 flex flex-wrap gap-2" aria-hidden="true">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} variant="text" width={100} height={20} borderRadius="9999px" />
        ))}
      </div>
      <div className="mt-4 flex gap-2 border-t border-slate-200 pt-4" aria-hidden="true">
        <Skeleton variant="text" width={80} height={36} borderRadius="lg" />
        <Skeleton variant="text" width={100} height={36} borderRadius="lg" />
      </div>
    </div>
  );
}