'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, ApiClientError } from '@/lib/api';
import { STATUS_LABELS, STATUS_STEPS, POLL_INTERVAL_MS } from '@/lib/constants';
import type { ReviewDetail } from '@/types/review';

interface ReviewStatusProps {
  reviewId: string;
  onCompleted: (review: ReviewDetail) => void;
  onError: (error: string) => void;
}

export function ReviewStatus({ reviewId, onCompleted, onError }: ReviewStatusProps) {
  const [currentStatus, setCurrentStatus] = useState<string>('pending');
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const review = await api.pollUntilCompleted(
        reviewId,
        (status) => setCurrentStatus(status),
        POLL_INTERVAL_MS,
      );
      onCompleted(review);
    } catch (err) {
      const message = err instanceof ApiClientError ? err.message : '获取审核状态失败';
      setError(message);
      onError(message);
    }
  }, [reviewId, onCompleted, onError]);

  useEffect(() => {
    poll();
  }, [poll]);

  const currentStepIndex = STATUS_STEPS.indexOf(currentStatus);

  return (
    <div className="w-full max-w-2xl">
      <h2 className="mb-8 text-center text-xl font-semibold text-gray-800">
        代码审核进行中
      </h2>

      {/* Progress Steps */}
      <div className="relative mb-8">
        <div className="absolute left-0 right-0 top-1/2 h-0.5 -translate-y-1/2 bg-gray-200">
          <div
            className="h-full bg-blue-500 transition-all duration-500"
            style={{
              width: `${Math.max(0, (currentStepIndex / (STATUS_STEPS.length - 1)) * 100)}%`,
            }}
          />
        </div>

        <div className="relative flex justify-between">
          {STATUS_STEPS.map((step, index) => {
            const isCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex;
            const isFailed = currentStatus === 'failed' && index === currentStepIndex;

            return (
              <div key={step} className="flex flex-col items-center">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-bold transition-colors ${
                    isCompleted
                      ? 'border-blue-500 bg-blue-500 text-white'
                      : isCurrent
                        ? isFailed
                          ? 'border-red-500 bg-red-500 text-white'
                          : 'border-blue-500 bg-white text-blue-500'
                        : 'border-gray-300 bg-white text-gray-400'
                  }`}
                >
                  {isCompleted ? (
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isCurrent && !isFailed ? (
                    <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : isFailed ? (
                    '✕'
                  ) : (
                    index + 1
                  )}
                </div>
                <span
                  className={`mt-2 text-xs ${
                    isCurrent
                      ? isFailed
                        ? 'font-medium text-red-600'
                        : 'font-medium text-blue-600'
                      : 'text-gray-500'
                  }`}
                >
                  {isCurrent && isFailed ? '失败' : STATUS_LABELS[step]}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Status message */}
      <div className="text-center">
        <p className="text-sm text-gray-600">
          {currentStatus === 'failed'
            ? error || '审核过程出现错误'
            : STATUS_LABELS[currentStatus] ?? '处理中...'}
        </p>
        {currentStatus !== 'failed' && (
          <div className="mt-4 flex justify-center">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-2 w-2 animate-bounce rounded-full bg-blue-400"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
