'use client';

import { Skeleton, SkeletonCard } from './Skeleton';

export function KPISkeleton({
  className = '',
  showSparkline = true,
  showSourceBadge = true,
}: {
  className?: string;
  showSparkline?: boolean;
  showSourceBadge?: boolean;
}) {
  return (
    <SkeletonCard className={`group relative overflow-hidden ${className}`} aria-hidden="true">
      <span className="absolute inset-x-5 top-0 h-px bg-gradient-to-r from-slate-600/30 via-slate-500/20 to-transparent" />
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Skeleton variant="circular" width={30} height={30} className="shrink-0" />
          <SkeletonText lines={1} />
        </div>
        <Skeleton variant="circular" width={6} height={6} />
      </div>
      <div className="mt-4 flex items-end justify-between gap-2">
        <div>
          <Skeleton variant="rectangular" width={120} height={32} className="font-variant-numeric" />
          <Skeleton variant="text" width="30%" height={10} />
        </div>
        <Skeleton variant="text" width={70} height={20} borderRadius="9999px" />
      </div>
      {showSparkline && (
        <div className="mt-3 h-7 w-full opacity-60">
          <Skeleton variant="rectangular" width="100%" height={28} borderRadius="4px" />
        </div>
      )}
      <div className="mt-3 flex items-end justify-between gap-2 border-t border-white/[0.07] pt-3 text-[10px]">
        {showSourceBadge ? (
          <Skeleton variant="text" width="140" height={16} />
        ) : (
          <Skeleton variant="text" width="80" height={12} />
        )}
        <Skeleton variant="text" width="60" height={12} />
      </div>
    </SkeletonCard>
  );
}

function SkeletonText({ lines = 1 }: { lines?: number }) {
  return (
    <div className="space-y-1" aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton key={index} variant="text" width={index === lines - 1 ? '70%' : '100%'} height={10} />
      ))}
    </div>
  );
}

export function KPIGridSkeleton({ count = 5 }: { count?: number }) {
  return (
    <section aria-label="Key performance indicators (loading)" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5" aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <KPISkeleton key={index} />
      ))}
    </section>
  );
}