'use client';

import { SEVERITY_LABELS, SEVERITY_COLORS } from '@/lib/constants';
import type { Severity } from '@/types/review';

interface SeverityBadgeProps {
  severity: Severity;
}

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const colorClass = SEVERITY_COLORS[severity] ?? SEVERITY_COLORS.info;
  const label = SEVERITY_LABELS[severity] ?? severity;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}
