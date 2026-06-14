'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { MarkdownReport } from '@/components/MarkdownReport';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';

function ResultContent() {
  const searchParams = useSearchParams();
  const dataParam = searchParams.get('data');

  if (!dataParam) {
    return (
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-8 text-center">
        <div className="mb-3 text-4xl">⚠️</div>
        <h2 className="text-lg font-semibold text-yellow-800">缺少审核数据</h2>
        <p className="mt-2 text-sm text-yellow-600">
          请先提交一个 PR 链接进行审核。
        </p>
        <a
          href="/"
          className="mt-4 inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          返回首页
        </a>
      </div>
    );
  }

  try {
    const result = JSON.parse(decodeURIComponent(dataParam));

    return (
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
            <div className="flex-1">
              <h1 className="mb-1 text-2xl font-bold text-gray-900">
                {result.pr_title}
              </h1>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600">
                <span>
                  {result.owner}/{result.repo}#{result.pull_number}
                </span>
                <span>模型: {result.model}</span>
                <span>
                  Token: {result.input_tokens} in / {result.output_tokens} out
                </span>
              </div>
            </div>
            <a
              href={result.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              在 GitHub 查看 →
            </a>
          </div>
        </div>

        {/* Markdown Report */}
        <MarkdownReport markdown={result.report} />
      </div>
    );
  } catch {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <div className="mb-3 text-4xl">❌</div>
        <h2 className="text-lg font-semibold text-red-800">数据解析失败</h2>
        <a
          href="/"
          className="mt-4 inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          返回首页
        </a>
      </div>
    );
  }
}

export default function ReviewResultPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-2xl py-12">
          <LoadingSkeleton lines={8} />
        </div>
      }
    >
      <ResultContent />
    </Suspense>
  );
}
