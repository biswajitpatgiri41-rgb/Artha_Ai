'use client';

import { Skeleton, SkeletonCard } from './index';

export function MacroSignalsSkeleton() {
  return (
    <SkeletonCard className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
      <div className="flex items-start justify-between" aria-hidden="true">
        <div className="space-y-1">
          <Skeleton variant="text" width="180" height={16} />
          <Skeleton variant="text" width="200" height={10} />
        </div>
        <Skeleton variant="text" width={100} height={20} borderRadius="9999px" />
      </div>
      <div className="mt-5 space-y-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="flex items-start gap-3 border-t border-white/[0.08] pt-3" aria-hidden="true">
            <Skeleton variant="circular" width={8} height={8} className="mt-1 shrink-0" />
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <Skeleton variant="text" width="120" height={10} />
                <Skeleton variant="text" width="80" height={10} />
              </div>
              <Skeleton variant="text" width="90%" height={10} />
            </div>
          </div>
        ))}
      </div>
    </SkeletonCard>
  );
}