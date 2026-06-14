'use client';

import { SCORE_THRESHOLDS } from '@/lib/constants';

interface ScoreGaugeProps {
  score: number | null;
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_MAP = {
  sm: { dimension: 80, strokeWidth: 6, fontSize: 'text-lg' },
  md: { dimension: 120, strokeWidth: 8, fontSize: 'text-2xl' },
  lg: { dimension: 160, strokeWidth: 10, fontSize: 'text-3xl' },
};

function getScoreInfo(score: number | null) {
  if (score === null || score === undefined) {
    return { label: '暂无', color: 'text-gray-400', fill: '#9ca3af' };
  }
  const threshold = SCORE_THRESHOLDS.find((t) => score >= t.min);
  return threshold ?? SCORE_THRESHOLDS[SCORE_THRESHOLDS.length - 1];
}

export function ScoreGauge({ score, size = 'md' }: ScoreGaugeProps) {
  const { dimension, strokeWidth, fontSize } = SIZE_MAP[size];
  const radius = (dimension - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = dimension / 2;

  const scoreInfo = getScoreInfo(score);
  const percentage = score !== null ? Math.min(100, Math.max(0, score)) : 0;
  const targetOffset = circumference * (1 - percentage / 100);

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={dimension} height={dimension} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
        />
        {/* Score arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={scoreInfo.fill}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          className="gauge-fill transition-all duration-1000"
          style={
            {
              '--target-offset': targetOffset,
              strokeDashoffset: targetOffset,
            } as React.CSSProperties
          }
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`${fontSize} font-bold ${scoreInfo.color}`}>
          {score ?? '-'}
        </span>
        <span className="text-xs text-gray-500">{scoreInfo.label}</span>
      </div>
    </div>
  );
}
