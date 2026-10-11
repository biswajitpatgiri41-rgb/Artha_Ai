'use client';

import {
  PageHeaderSkeleton,
  SkeletonCard,
  SkeletonCardHeader,
  SkeletonCardContent,
  Skeleton,
  TableSkeleton,
} from './index';

export function DataSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      <PageHeaderSkeleton wide />

      {/* Data Upload Manager */}
      <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="space-y-4" aria-hidden="true">
            <div className="flex items-center justify-between">
              <Skeleton variant="text" width="200" height={16} />
              <Skeleton variant="text" width={120} height={40} borderRadius="lg" />
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} variant="text" width="100%" height={48} borderRadius="xl" />
              ))}
            </div>
          </div>
        </SkeletonCardContent>
      </SkeletonCard>

      {/* Demo Catalog Notice */}
      <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.07] flex items-start gap-3 p-4">
        <Skeleton variant="circular" width={17} height={17} className="mt-0.5 shrink-0" />
        <div className="space-y-1 flex-1">
          <Skeleton variant="text" width="100" height={10} />
          <Skeleton variant="text" width="300" height={8} />
        </div>
      </SkeletonCard>

      {/* Series Registry - Search/Filter */}
      <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between" aria-hidden="true">
            <div className="space-y-1">
              <Skeleton variant="text" width="100" height={10} className="uppercase tracking-[0.18em]" />
              <Skeleton variant="text" width="200" height={24} />
            </div>
            <div className="flex items-center gap-3">
              <Skeleton variant="text" width={240} height={40} borderRadius="xl" />
              <Skeleton variant="text" width={160} height={40} borderRadius="xl" />
            </div>
          </div>
        </SkeletonCardContent>
      </SkeletonCard>

      {/* Table with Series */}
      <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <div className="mb-4 flex items-center justify-between" aria-hidden="true">
          <Skeleton variant="text" width="100" height={12} />
          <Skeleton variant="text" width={100} height={12} />
        </div>
        <TableSkeleton rows={10} columns={8} />
      </SkeletonCard>

      {/* Series Detail Panel */}
      <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
        <SkeletonCardHeader showIcon={false} showBadge={false} />
        <SkeletonCardContent>
          <div className="flex items-start justify-between gap-3" aria-hidden="true">
            <div className="space-y-1">
              <Skeleton variant="text" width="100" height={10} className="uppercase tracking-[0.16em]" />
              <Skeleton variant="text" width="200" height={24} />
            </div>
            <Skeleton variant="text" width={120} height={40} borderRadius="lg" />
          </div>
          <Skeleton variant="text" width="80%" height={10} className="mt-4" />
          <dl className="mt-5 divide-y divide-slate-100 border-y border-slate-100" aria-hidden="true">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="flex items-start justify-between gap-4 py-3">
                <Skeleton variant="text" width="100" height={10} />
                <Skeleton variant="text" width="60%" height={10} className="text-right font-medium" />
              </div>
            ))}
          </dl>
          <div className="mt-5" aria-hidden="true">
            <Skeleton variant="text" width="120" height={10} className="uppercase tracking-[0.12em]" />
            <div className="mt-3 space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                  <Skeleton variant="text" width="80" height={10} />
                  <Skeleton variant="text" width="80" height={12} className="font-semibold" />
                </div>
              ))}
            </div>
          </div>
        </SkeletonCardContent>
      </SkeletonCard>
    </div>
  );
}