'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { ReviewStatus } from '@/components/ReviewStatus';
import { ReviewReport } from '@/components/ReviewReport';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import type { ReviewDetail } from '@/types/review';

export default function ReviewDetailPage() {
  const params = useParams();
  const reviewId = params.id as string;

  const [state, setState] = useState<'loading' | 'pending' | 'completed' | 'error'>('loading');
  const [review, setReview] = useState<ReviewDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCompleted = useCallback((result: ReviewDetail) => {
    setReview(result);
    setState('completed');
  }, []);

  const handleError = useCallback((msg: string) => {
    setError(msg);
    setState('error');
  }, []);

  return (
    <div className="flex flex-col items-center">
      {state === 'loading' && (
        <div className="w-full max-w-2xl py-12">
          <LoadingSkeleton lines={6} />
        </div>
      )}

      {state === 'pending' && (
        <ReviewStatus
          reviewId={reviewId}
          onCompleted={handleCompleted}
          onError={handleError}
        />
      )}

      {state === 'completed' && review && (
        <ReviewReport review={review} />
      )}

      {state === 'error' && (
        <div className="w-full max-w-2xl">
          <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
            <div className="mb-3 text-4xl">❌</div>
            <h2 className="mb-2 text-lg font-semibold text-red-800">
              审核失败
            </h2>
            <p className="mb-4 text-sm text-red-600">
              {error || '未知错误'}
            </p>
            <button
              onClick={() => {
                setState('pending');
                setError(null);
              }}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
            >
              重试
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
