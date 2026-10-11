'use client';

import { Skeleton, SkeletonCard, SkeletonCardHeader, SkeletonCardContent, ArchitectureGraphContent } from './index';

export function ArchitectureSkeleton() {
  return (
    <div className="space-y-5" aria-hidden="true">
      <HeaderBarSkeleton />
      <ArchitectureGraphSkeleton />
    </div>
  );
}

function HeaderBarSkeleton() {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cyan-300/10 bg-cyan-400/[0.035] px-4 py-3" aria-hidden="true">
      <Skeleton variant="text" width="300" height={10} />
      <Skeleton variant="text" width={140} height={20} borderRadius="9999px" />
    </div>
  );
}

function ArchitectureGraphSkeleton() {
  return (
    <SkeletonCard variant="elevated" className="relative overflow-hidden">
      <SkeletonCardHeader showIcon={false} showBadge={false} />
      <SkeletonCardContent>
        <ArchitectureGraphContent />
      </SkeletonCardContent>
    </SkeletonCard>
  );
}
