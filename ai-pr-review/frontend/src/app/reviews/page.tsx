'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, ApiClientError } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import { SEVERITY_LABELS } from '@/lib/constants';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import type { Review } from '@/types/review';

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  fetching: 'bg-blue-100 text-blue-800',
  analyzing: 'bg-indigo-100 text-indigo-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

const STATUS_LABEL: Record<string, string> = {
  pending: '等待中',
  fetching: '获取中',
  analyzing: '分析中',
  completed: '已完成',
  failed: '失败',
};

export default function ReviewsListPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const perPage = 20;

  useEffect(() => {
    const fetchReviews = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.listReviews(page, perPage);
        setReviews(result.items);
        setTotal(result.total);
      } catch (err) {
        setError(err instanceof ApiClientError ? err.message : '加载失败');
      } finally {
        setLoading(false);
      }
    };
    fetchReviews();
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">审核历史</h1>

      {loading && <LoadingSkeleton lines={5} />}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && reviews.length === 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-12 text-center">
          <div className="mb-3 text-4xl">📋</div>
          <h3 className="mb-2 text-lg font-medium text-gray-900">还没有审核记录</h3>
          <p className="mb-4 text-sm text-gray-500">
            去首页提交一个 Pull Request 开始你的第一次审核
          </p>
          <Link
            href="/"
            className="inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            提交审核
          </Link>
        </div>
      )}

      {!loading && !error && reviews.length > 0 && (
        <>
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    PR 链接
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    状态
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                    问题数
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    时间
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {reviews.map((review) => (
                  <tr
                    key={review.id}
                    className="transition-colors hover:bg-gray-50"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/reviews/${review.id}`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-800"
                      >
                        {truncatePRUrl(review.pr_url)}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          STATUS_BADGE[review.status] ?? 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {STATUS_LABEL[review.status] ?? review.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-sm text-gray-600">
                      {(review as any).total_issues ?? '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {formatDateTime((review as any).created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
              >
                上一页
              </button>
              <span className="text-sm text-gray-600">
                第 {page} / {totalPages} 页
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function truncatePRUrl(url: string): string {
  try {
    const u = new URL(url);
    return u.pathname.slice(1);
  } catch {
    return url.length > 50 ? url.slice(0, 47) + '…' : url;
  }
}
