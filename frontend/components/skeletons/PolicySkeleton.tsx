'use client';

import {
  PageHeaderSkeleton,
  SkeletonCard,
  SkeletonCardHeader,
  SkeletonCardContent,
  Skeleton,
} from './index';
import { DecisionMatrixSkeleton } from './DecisionMatrixSkeleton';
import { EvidenceRegisterSkeleton } from './EvidenceRegisterSkeleton';

export function PolicySkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      <PageHeaderSkeleton wide />
      <WarningNoticeSkeleton />
      <MainGridSkeleton />
      <DecisionMatrixSkeleton />
      <EvidenceRegisterSkeleton />
    </div>
  );
}

function WarningNoticeSkeleton() {
  return (
    <SkeletonCard variant="outlined" className="border-rose-300/15 bg-rose-400/[0.07] flex items-start gap-3 p-4">
      <Skeleton variant="circular" width={17} height={17} className="mt-0.5 shrink-0" />
      <Skeleton variant="text" width="300" height={10} />
    </SkeletonCard>
  );
}

function MainGridSkeleton() {
  return (
    <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
      <RecommendationCardSkeleton />
      <HowToReadCardSkeleton />
    </div>
  );
}

function RecommendationCardSkeleton() {
  return (
    <SkeletonCard variant="outlined" className="border-blue-200 bg-blue-50/60 p-5 shadow-sm">
      <SkeletonCardHeader showIcon={false} showBadge={false} />
      <SkeletonCardContent>
        <div className="flex items-start justify-between gap-4" aria-hidden="true">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Skeleton variant="circular" width={17} height={17} />
              <Skeleton variant="text" width="140" height={10} />
            </div>
            <Skeleton variant="text" width="60%" height={32} />
            <Skeleton variant="text" width="80%" height={16} className="mt-2" />
          </div>
          <Skeleton variant="text" width={80} height={20} borderRadius="md" />
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2" aria-hidden="true">
          <div>
            <Skeleton variant="text" width="60" height={10} className="uppercase tracking-[0.12em]" />
            <Skeleton variant="text" width="80" height={28} className="mt-1 font-semibold" />
            <Skeleton variant="rectangular" width="100%" height={8} borderRadius="9999px" className="mt-2" />
          </div>
          <div>
            <Skeleton variant="text" width="40" height={10} className="uppercase tracking-[0.12em]" />
            <Skeleton variant="text" width="60%" height={16} className="mt-1 font-semibold" />
            <Skeleton variant="text" width="80%" height={10} className="mt-2" />
          </div>
        </div>
      </SkeletonCardContent>
    </SkeletonCard>
  );
}

function HowToReadCardSkeleton() {
  return (
    <SkeletonCard variant="outlined" className="border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
      <SkeletonCardHeader showIcon={true} showBadge={false} />
      <SkeletonCardContent>
        <SkeletonText lines={3} className="mt-3" />
        <Skeleton variant="text" width="120" height={10} className="mt-4 uppercase tracking-[0.12em]" />
      </SkeletonCardContent>
    </SkeletonCard>
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