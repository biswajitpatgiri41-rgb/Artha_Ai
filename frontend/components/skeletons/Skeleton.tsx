'use client';

import { useSyncExternalStore } from 'react';

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
}

const BASE_SKELETON_STYLES = `
  relative overflow-hidden
  bg-gradient-to-r
  from-slate-800/60
  via-slate-700/40
  to-slate-800/60
  border border-white/[0.06]
  backdrop-blur-sm
`;

export function Skeleton({
  className = '',
  style,
  variant = 'text',
  width,
  height,
  borderRadius,
}: SkeletonProps) {
  const prefersReducedMotion = useSyncExternalStore(
    (onChange) => {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      mediaQuery.addEventListener('change', onChange);
      return () => mediaQuery.removeEventListener('change', onChange);
    },
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    () => true,
  );

  const shimmerStyle: React.CSSProperties = {
    ...style,
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
    borderRadius: borderRadius,
    backgroundSize: '200% 100%',
    backgroundPosition: '200% 0',
    animation: prefersReducedMotion
      ? 'none'
      : 'skeleton-shimmer 1.8s ease-in-out infinite',
  };

  const variantStyles = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-xl',
  };

  return (
    <div
      className={`${BASE_SKELETON_STYLES} ${variantStyles[variant]} ${className}`}
      style={shimmerStyle}
      aria-hidden="true"
    />
  );
}

export function SkeletonText({ lines = 1, className = '', ...props }: Omit<SkeletonProps, 'variant'> & { lines?: number }) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          width={index === lines - 1 ? '60%' : '100%'}
          height={12}
          {...props}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({
  className = '',
  style,
  children,
  padding = 'p-5',
}: {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
  padding?: string;
}) {
  return (
    <div
      className={`rounded-[18px] border border-white/[0.08] bg-[rgba(15,23,42,0.62)] backdrop-blur-2xl shadow-[0_18px_45px_rgba(0,0,0,0.2)] ${padding} ${className}`}
      style={style}
      aria-hidden="true"
    >
      {children}
    </div>
  );
}
