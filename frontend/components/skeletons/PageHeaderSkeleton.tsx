'use client';

import { Skeleton } from './Skeleton';

interface PageHeaderSkeletonProps {
  className?: string;
  showEyebrow?: boolean;
  showBadges?: boolean;
  badgeCount?: number;
  wide?: boolean;
}

export function PageHeaderSkeleton({
  className = '',
  showEyebrow = true,
  showBadges = true,
  badgeCount = 2,
  wide = false,
}: PageHeaderSkeletonProps) {
  return (
    <header className={`relative mb-8 overflow-hidden border-b border-white/[0.08] pb-7 pt-2 ${wide ? 'md:flex md:items-end md:justify-between' : ''} ${className}`} aria-hidden="true">
      <div className="pointer-events-none absolute -left-20 -top-24 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-cyan-400/[0.06] blur-3xl" />
      <div className="relative">
        {showEyebrow && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Skeleton variant="text" width={160} height={10} />
            {showBadges && (
              <>
                <Skeleton variant="text" width={100} height={18} borderRadius="9999px" />
                <Skeleton variant="text" width={80} height={18} borderRadius="9999px" />
              </>
            )}
          </div>
        )}
        <Skeleton variant="text" width={wide ? '60%' : '50%'} height={40} />
        <SkeletonText lines={2} className="mt-2 max-w-2xl" />
      </div>
    </header>
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

export function CategorySelectorSkeleton({
  className = '',
  tabs = 4,
}: {
  className?: string;
  tabs?: number;
}) {
  return (
    <div className={`flex flex-wrap items-center gap-1.5 rounded-2xl border border-white/[0.08] bg-white/[0.035] p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)] backdrop-blur-xl ${className}`} aria-hidden="true" role="tablist">
      {Array.from({ length: tabs }).map((_, index) => (
        <div key={index} className="flex min-w-[132px] flex-1 items-center gap-2 rounded-xl border px-3 py-2" aria-hidden="true">
          <Skeleton variant="circular" width={15} height={15} />
          <div className="space-y-1">
            <Skeleton variant="text" width="60%" height={10} />
            <Skeleton variant="text" width="80%" height={8} />
          </div>
        </div>
      ))}
      <Skeleton variant="text" width={100} height={8} className="hidden px-2 xl:block" />
    </div>
  );
}