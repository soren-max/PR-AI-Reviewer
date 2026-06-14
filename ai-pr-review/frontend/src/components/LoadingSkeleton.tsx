'use client';

interface LoadingSkeletonProps {
  lines?: number;
  className?: string;
}

export function LoadingSkeleton({ lines = 3, className = '' }: LoadingSkeletonProps) {
  return (
    <div className={`animate-pulse space-y-3 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-gray-200"
          style={{ width: `${70 + Math.random() * 30}%` }}
        />
      ))}
      <span className="sr-only">加载中...</span>
    </div>
  );
}
