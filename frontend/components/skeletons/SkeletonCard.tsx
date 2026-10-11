'use client';

import { Skeleton } from './Skeleton';

interface SkeletonCardProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
  padding?: string;
  variant?: 'default' | 'elevated' | 'outlined';
}

const VARIANT_STYLES = {
  default: 'rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] p-5 shadow-[0_18px_45px_rgba(0,0,0,0.2)] backdrop-blur-2xl',
  elevated: 'rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.66)] p-5 shadow-[0_20px_55px_rgba(0,0,0,0.25)] backdrop-blur-2xl',
  outlined: 'rounded-xl border border-white/[0.07] bg-white/[0.035] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)]',
};

export function SkeletonCard({
  className = '',
  style,
  children,
  padding,
  variant = 'default',
}: SkeletonCardProps) {
  return (
    <div
      className={`${VARIANT_STYLES[variant]} ${className}`}
      style={style}
      aria-hidden="true"
    >
      {children}
    </div>
  );
}

export function SkeletonCardHeader({
  className = '',
  showIcon = true,
  showBadge = false,
}: {
  className?: string;
  showIcon?: boolean;
  showBadge?: boolean;
}) {
  return (
    <div className={`flex items-start justify-between gap-4 ${className}`} aria-hidden="true">
      <div className="flex items-center gap-2">
        {showIcon && <Skeleton variant="circular" width={32} height={32} className="shrink-0" />}
        <div className="space-y-1">
          <Skeleton variant="text" width="40%" height={20} />
          <Skeleton variant="text" width="60%" height={12} />
        </div>
      </div>
      {showBadge && <Skeleton variant="text" width={80} height={20} borderRadius="9999px" />}
    </div>
  );
}

export function SkeletonCardContent({
  className = '',
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  return <div className={`mt-5 ${className}`} aria-hidden="true">{children}</div>;
}

export function SkeletonCardFooter({
  className = '',
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  return <div className={`mt-4 border-t border-white/[0.07] pt-4 ${className}`} aria-hidden="true">{children}</div>;
}