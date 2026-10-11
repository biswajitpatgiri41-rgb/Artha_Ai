'use client';

import { SkeletonCard, SkeletonCardHeader, SkeletonCardContent, Skeleton } from './index';

export function ShockConfigSkeleton() {
  return (
    <SkeletonCard>
      <SkeletonCardHeader showIcon={true} showBadge={true} />
      <SkeletonCardContent>
        <div className="mt-6 space-y-6" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="block">
              <div className="flex items-center justify-between gap-3 text-xs">
                <Skeleton variant="text" width="60%" height={10} />
                <div className="flex items-center gap-1">
                  <Skeleton variant="text" width={50} height={12} borderRadius="md" />
                  <Skeleton variant="text" width={20} height={10} />
                </div>
              </div>
              <Skeleton variant="rectangular" width="100%" height={24} className="mt-3" borderRadius="8px" />
              <div className="mt-1 flex justify-between">
                <Skeleton variant="text" width={30} height={8} />
                <Skeleton variant="text" width={30} height={8} />
              </div>
            </div>
          ))}
          <div>
            <div className="flex items-center justify-between gap-3 text-xs">
              <Skeleton variant="text" width="60%" height={10} />
              <div className="flex items-center gap-1">
                <Skeleton variant="text" width={50} height={12} borderRadius="md" />
                <Skeleton variant="text" width={20} height={10} />
              </div>
            </div>
            <Skeleton variant="rectangular" width="100%" height={24} className="mt-3" borderRadius="8px" />
            <div className="mt-1 flex justify-between">
              <Skeleton variant="text" width={40} height={8} />
              <Skeleton variant="text" width={40} height={8} />
            </div>
          </div>
          <div>
            <Skeleton variant="text" width="40%" height={10} className="uppercase tracking-[0.12em]" />
            <Skeleton variant="text" width="100%" height={40} borderRadius="md" className="mt-2" />
          </div>
          <div>
            <Skeleton variant="text" width="40%" height={10} className="uppercase tracking-[0.12em]" />
            <div className="mt-2 grid grid-cols-3 gap-2">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} variant="text" width="100%" height={36} borderRadius="lg" />
              ))}
            </div>
          </div>
        </div>
      </SkeletonCardContent>
    </SkeletonCard>
  );
}