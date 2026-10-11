'use client';

import { SkeletonCard, SkeletonCardHeader, SkeletonCardContent, Skeleton } from './index';

export function EvidenceRegisterSkeleton() {
  return (
    <SkeletonCard variant="outlined" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
      <SkeletonCardHeader showIcon={true} showBadge={false} />
      <SkeletonCardContent>
        <div className="mt-4 overflow-x-auto" aria-hidden="true">
          <table className="w-full min-w-[680px] text-left text-xs">
            <thead className="border-b border-slate-200 text-[10px] uppercase tracking-[0.12em] text-slate-400">
              <tr>
                {['Option', 'Dimensions compared', 'Evidence', 'Status'].map((header) => (
                  <th key={header} className="pb-3 font-semibold">
                    <Skeleton variant="text" width="80%" height={10} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {Array.from({ length: 3 }).map((_, rowIndex) => (
                <tr key={rowIndex}>
                  <td className="py-3">
                    <Skeleton variant="text" width="70%" height={12} className="font-semibold" />
                  </td>
                  <td className="py-3">
                    <Skeleton variant="text" width="80%" height={10} />
                  </td>
                  <td className="py-3">
                    <div className="flex flex-wrap gap-1">
                      {Array.from({ length: 3 }).map((_, i) => (
                        <Skeleton key={i} variant="text" width={80} height={20} borderRadius="9999px" />
                      ))}
                    </div>
                  </td>
                  <td className="py-3">
                    <Skeleton variant="text" width="80%" height={10} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SkeletonCardContent>
    </SkeletonCard>
  );
}