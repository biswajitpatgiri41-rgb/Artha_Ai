'use client';

import {
  PageHeaderSkeleton,
  SkeletonCard,
  Skeleton,
} from './index';
import { ShockConfigSkeleton } from './ShockConfigSkeleton';
import { ScenarioOutputSkeleton } from './ScenarioOutputSkeleton';
import { LowerSectionSkeleton } from './LowerSectionSkeleton';

export function SimulatorSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      <PageHeaderSkeleton wide />
      <MockNoticeSkeleton />
      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
        <ShockConfigSkeleton />
        <ScenarioOutputSkeleton />
      </div>
      <LowerSectionSkeleton />
    </div>
  );
}

function MockNoticeSkeleton() {
  return (
    <SkeletonCard variant="outlined" className="border-amber-300/15 bg-amber-400/[0.07] flex items-start gap-3 p-4">
      <Skeleton variant="circular" width={16} height={16} className="mt-0.5 shrink-0" />
      <div className="space-y-1 flex-1">
        <Skeleton variant="text" width="100" height={10} />
        <Skeleton variant="text" width="250" height={8} />
      </div>
    </SkeletonCard>
  );
}