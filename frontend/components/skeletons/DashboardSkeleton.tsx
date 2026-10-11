'use client';

import {
  PageHeaderSkeleton,
  CategorySelectorSkeleton,
  KPIGridSkeleton,
  ChartSkeleton,
  DonutChartSkeleton,
  ScenarioLabSkeleton,
  PolicyIntelligenceSkeleton,
  MacroSignalsSkeleton,
  AgentTimelineSkeleton,
  SkeletonCard,
  SkeletonCardHeader,
  SkeletonCardContent,
  SkeletonCardFooter,
  Skeleton,
} from './index';

export function DashboardSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      {/* Page Header */}
      <PageHeaderSkeleton wide />

      {/* Macro Category Selector */}
      <CategorySelectorSkeleton tabs={4} />

      {/* KPI Row */}
      <KPIGridSkeleton count={5} />

      {/* Main Chart Section */}
      <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
        <ChartSkeleton height={350} headerBadge footerItems={3} />
        <DonutChartSkeleton size={245} legendItems={3} />
      </div>

      {/* Lower Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Scenario Lab Skeleton */}
        <ScenarioLabSkeleton />
        {/* Policy Intelligence Skeleton */}
        <PolicyIntelligenceSkeleton />
      </div>

      {/* Bottom Section - Macro Signals & Agent Timeline */}
      <div className="grid gap-5 xl:grid-cols-[1fr_1.15fr]">
        <MacroSignalsSkeleton />
        <AgentTimelineSkeleton />
      </div>
    </div>
  );
}
