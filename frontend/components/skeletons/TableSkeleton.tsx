'use client';

import { Skeleton } from './Skeleton';

interface TableSkeletonProps {
  className?: string;
  columns?: number;
  rows?: number;
  columnWidths?: (string | number)[];
  showHeader?: boolean;
  striped?: boolean;
}

export function TableSkeleton({
  className = '',
  columns = 6,
  rows = 8,
  columnWidths,
  showHeader = true,
  striped = false,
}: TableSkeletonProps) {
  const defaultWidths = ['28%', '12%', '10%', '12%', '14%', '12%', '10%', '10%'];
  const widths = columnWidths?.length ? columnWidths : defaultWidths.slice(0, columns);

  return (
    <div className={`overflow-x-auto ${className}`} aria-hidden="true" role="table">
      <table className="w-full min-w-[820px] text-left text-xs">
        {showHeader && (
          <thead className="border-b border-white/[0.08]" aria-hidden="true">
            <tr>
              {widths.map((width, index) => (
                <th key={index} className="pb-3 font-semibold" style={{ width: typeof width === 'number' ? `${width}px` : width }}>
                  <Skeleton variant="text" width="80%" height={10} />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="divide-y divide-white/[0.07]" aria-hidden="true">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex} className={striped && rowIndex % 2 === 0 ? 'bg-white/[0.02]' : ''}>
              {widths.map((width, colIndex) => (
                <td key={colIndex} className="py-3 pr-3" style={{ width: typeof width === 'number' ? `${width}px` : width }}>
                  {colIndex === 0 ? (
                    <div className="space-y-1">
                      <Skeleton variant="text" width="70%" height={12} />
                      <Skeleton variant="text" width="40%" height={8} />
                    </div>
                  ) : colIndex === 1 || colIndex === 4 ? (
                    <Skeleton variant="text" width="60%" height={12} />
                  ) : (
                    <Skeleton variant="text" width="50%" height={10} />
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TableRowSkeleton({
  columns = 6,
  className = '',
  columnWidths,
}: {
  columns?: number;
  className?: string;
  columnWidths?: (string | number)[];
}) {
  const defaultWidths = ['28%', '12%', '10%', '12%', '14%', '12%', '10%', '10%'];
  const widths = columnWidths?.length ? columnWidths : defaultWidths.slice(0, columns);

  return (
    <tr className={className} aria-hidden="true">
      {widths.map((width, colIndex) => (
        <td key={colIndex} className="py-3 pr-3" style={{ width: typeof width === 'number' ? `${width}px` : width }}>
          {colIndex === 0 ? (
            <div className="space-y-1">
              <Skeleton variant="text" width="70%" height={12} />
              <Skeleton variant="text" width="40%" height={8} />
            </div>
          ) : (
            <Skeleton variant="text" width="60%" height={10} />
          )}
        </td>
      ))}
    </tr>
  );
}

export function TableHeaderSkeleton({
  columns = 6,
  className = '',
  columnWidths,
}: {
  columns?: number;
  className?: string;
  columnWidths?: (string | number)[];
}) {
  const defaultWidths = ['28%', '12%', '10%', '12%', '14%', '12%', '10%', '10%'];
  const widths = columnWidths?.length ? columnWidths : defaultWidths.slice(0, columns);

  return (
    <thead className={`border-b border-white/[0.08] ${className}`} aria-hidden="true">
      <tr>
        {widths.map((width, index) => (
          <th key={index} className="pb-3 font-semibold" style={{ width: typeof width === 'number' ? `${width}px` : width }}>
            <Skeleton variant="text" width="80%" height={10} />
          </th>
        ))}
      </tr>
    </thead>
  );
}