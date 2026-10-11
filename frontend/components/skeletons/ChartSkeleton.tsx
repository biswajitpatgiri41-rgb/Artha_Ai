'use client';

import { Skeleton } from './Skeleton';
import { SkeletonCard, SkeletonCardHeader, SkeletonCardContent, SkeletonCardFooter } from './SkeletonCard';

interface ChartSkeletonProps {
  className?: string;
  height?: string | number;
  showHeader?: boolean;
  headerIcon?: boolean;
  headerBadge?: boolean;
  showFooter?: boolean;
  footerItems?: number;
}

export function ChartSkeleton({
  className = '',
  height = 320,
  showHeader = true,
  headerIcon = true,
  headerBadge = false,
  showFooter = true,
  footerItems = 3,
}: ChartSkeletonProps) {
  return (
    <SkeletonCard className={className} aria-hidden="true">
      {showHeader && (
        <SkeletonCardHeader showIcon={headerIcon} showBadge={headerBadge} />
      )}
      <SkeletonCardContent>
        <Skeleton variant="rectangular" width="100%" height={height} borderRadius="8px" />
      </SkeletonCardContent>
      {showFooter && (
        <SkeletonCardFooter>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1" aria-hidden="true">
            {Array.from({ length: footerItems }).map((_, index) => (
              <Skeleton key={index} variant="text" width={index === 0 ? 160 : index === 1 ? 100 : 140} height={10} />
            ))}
          </div>
        </SkeletonCardFooter>
      )}
    </SkeletonCard>
  );
}

export function DonutChartSkeleton({
  className = '',
  size = 245,
  showHeader = true,
  showLegend = true,
  legendItems = 3,
}: {
  className?: string;
  size?: number;
  showHeader?: boolean;
  showLegend?: boolean;
  legendItems?: number;
}) {
  return (
    <SkeletonCard className={className} aria-hidden="true">
      {showHeader && (
        <SkeletonCardHeader showIcon={true} showBadge={true} />
      )}
      <SkeletonCardContent>
        <div className="flex items-center justify-center" style={{ height: size }} aria-hidden="true">
          <Skeleton variant="circular" width={size * 0.8} height={size * 0.8} />
        </div>
      </SkeletonCardContent>
      {showLegend && (
        <SkeletonCardFooter>
          <div className="space-y-2" aria-hidden="true">
            {Array.from({ length: legendItems }).map((_, index) => (
              <div key={index} className="flex items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <Skeleton variant="circular" width={8} height={8} />
                  <Skeleton variant="text" width={80} height={12} />
                </div>
                <Skeleton variant="text" width={40} height={12} />
              </div>
            ))}
          </div>
        </SkeletonCardFooter>
      )}
    </SkeletonCard>
  );
}

export function SparklineSkeleton({
  className = '',
  width = '100%',
  height = 28,
}: {
  className?: string;
  width?: string | number;
  height?: string | number;
}) {
  return (
    <Skeleton variant="rectangular" width={width} height={height} borderRadius="4px" className={`opacity-60 ${className}`} aria-hidden="true" />
  );
}
