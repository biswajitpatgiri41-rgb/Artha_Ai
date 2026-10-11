'use client';

import { SkeletonCard, Skeleton } from './index';

export function DecisionMatrixSkeleton() {
  return (
    <div aria-hidden="true">
      <div className="mb-3 flex items-end justify-between gap-4">
        <div className="space-y-1">
          <Skeleton variant="text" width="100" height={10} className="uppercase tracking-[0.18em]" />
          <Skeleton variant="text" width="160" height={24} />
        </div>
        <Skeleton variant="text" width="120" height={10} />
      </div>
      <div className="grid gap-5 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <SkeletonCard key={index} variant="outlined" className="bg-white p-5 shadow-sm shadow-slate-200/40">
            <PolicyAlternativeSkeleton />
          </SkeletonCard>
        ))}
      </div>
    </div>
  );
}

function PolicyAlternativeSkeleton() {
  return (
    <div aria-hidden="true">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <Skeleton variant="text" width="120" height={16} />
          <Skeleton variant="text" width="80" height={10} />
        </div>
        <Skeleton variant="text" width={100} height={20} borderRadius="md" />
      </div>
      <Skeleton variant="text" width="90%" height={10} className="mt-4 min-h-12" />
      <SkeletonCard variant="outlined" className="mt-5">
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i}>
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
      </SkeletonCard>
      <Skeleton variant="rectangular" width="100%" height={8} borderRadius="9999px" className="mt-5" />
      <div className="mt-5 border-t pt-4">
        <Skeleton variant="text" width="60" height={10} className="uppercase tracking-[0.12em]" />
        <div className="mt-3 flex flex-wrap gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} variant="text" width={100} height={20} borderRadius="9999px" />
          ))}
        </div>
      </div>
      <div className="mt-5 grid gap-4 border-t pt-4">
        <div>
          <Skeleton variant="text" width="60" height={10} className="uppercase tracking-[0.12em]" />
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} variant="text" width="80%" height={10} className="mt-1" />
          ))}
        </div>
        <div>
          <Skeleton variant="text" width="60" height={10} className="uppercase tracking-[0.12em]" />
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} variant="text" width="80%" height={10} className="mt-1" />
          ))}
        </div>
      </div>
    </div>
  );
}

function SkeletonText({ lines = 1, className = '' }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton key={index} variant="text" width={index === lines - 1 ? '70%' : '100%'} height={16} />
      ))}
    </div>
  );
}
