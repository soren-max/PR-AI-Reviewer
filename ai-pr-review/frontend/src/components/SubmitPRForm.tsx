'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiClientError } from '@/lib/api';

const PR_URL_REGEX = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/pull\/\d+(\/.*)?$/;

export function SubmitPRForm() {
  const router = useRouter();
  const [prUrl, setPrUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const validate = (url: string): boolean => {
    if (!url.trim()) {
      setError('请输入 GitHub Pull Request 链接');
      return false;
    }
    if (!PR_URL_REGEX.test(url.trim())) {
      setError('请输入有效的 GitHub PR 链接，例如：https://github.com/owner/repo/pull/42');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!validate(prUrl)) return;

    setLoading(true);
    try {
      // Call the synchronous review endpoint (waits for LLM result)
      const result = await api.reviewSync({ pr_url: prUrl.trim() });
      // Navigate to result page with the markdown report
      const encoded = encodeURIComponent(JSON.stringify(result));
      router.push(`/review/result?data=${encoded}`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError('审核请求失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="mb-4">
        <label htmlFor="pr-url" className="mb-2 block text-sm font-medium text-gray-700">
          GitHub Pull Request 链接
        </label>
        <div className="flex gap-2">
          <input
            id="pr-url"
            type="url"
            value={prUrl}
            onChange={(e) => {
              setPrUrl(e.target.value);
              setError(null);
            }}
            placeholder="https://github.com/owner/repo/pull/42"
            className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm shadow-sm transition-colors focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            disabled={loading}
            autoFocus
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                分析中...
              </span>
            ) : (
              '开始审核'
            )}
          </button>
        </div>
        {loading && (
          <p className="mt-2 text-xs text-gray-500">
            正在获取 PR 信息并调用 AI 分析，大文件可能需要 30-60 秒
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">
          {error}
        </div>
      )}
    </form>
  );
}
