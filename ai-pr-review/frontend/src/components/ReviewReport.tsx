'use client';

import { useState } from 'react';
import { ScoreGauge } from './ScoreGauge';
import { CommentCard } from './CommentCard';
import { FileTree } from './FileTree';
import { formatDateTime, formatDuration } from '@/lib/utils';
import { SEVERITY_LABELS } from '@/lib/constants';
import type { ReviewDetail, Severity } from '@/types/review';

interface ReviewReportProps {
  review: ReviewDetail;
}

export function ReviewReport({ review }: ReviewReportProps) {
  const [activeFile, setActiveFile] = useState<string | null>(null);

  // Group comments by file
  const commentsByFile: Record<string, typeof review.comments> = {};
  for (const c of review.comments) {
    if (!commentsByFile[c.file_path]) commentsByFile[c.file_path] = [];
    commentsByFile[c.file_path].push(c);
  }

  const filePaths = review.files.map((f) => f.file_path);
  const filteredFiles = activeFile
    ? filePaths.filter((fp) => fp === activeFile)
    : filePaths;

  return (
    <div className="w-full max-w-6xl">
      {/* Header: PR info */}
      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <h1 className="mb-2 text-2xl font-bold text-gray-900">
              {review.pr_info?.title || 'PR Review Report'}
            </h1>
            <div className="flex flex-wrap gap-4 text-sm text-gray-600">
              <span>
                {review.pr_info?.owner}/{review.pr_info?.repo}#{review.pr_info?.number}
              </span>
              <span>作者: {review.pr_info?.author || '-'}</span>
              <span>
                {review.pr_info?.head_branch} → {review.pr_info?.base_branch}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-400">
              <span>创建: {formatDateTime(review.created_at)}</span>
              {review.completed_at && (
                <span>完成: {formatDateTime(review.completed_at)}</span>
              )}
              {review.duration_ms && (
                <span>耗时: {formatDuration(review.duration_ms)}</span>
              )}
            </div>
          </div>

          {/* Score gauge */}
          <div className="flex-shrink-0">
            <ScoreGauge score={review.summary?.overall_score ?? null} size="md" />
          </div>
        </div>

        {/* Stats */}
        {review.summary && (
          <div className="mt-4 flex gap-4 border-t border-gray-100 pt-4">
            <StatItem label="总问题" value={review.summary.total_issues} />
            <StatItem label={SEVERITY_LABELS.critical} value={review.summary.critical} color="text-red-600" />
            <StatItem label={SEVERITY_LABELS.major} value={review.summary.major} color="text-orange-600" />
            <StatItem label={SEVERITY_LABELS.minor} value={review.summary.minor} color="text-yellow-600" />
            <StatItem label={SEVERITY_LABELS.info} value={review.summary.info} color="text-gray-600" />
          </div>
        )}

        {/* Error */}
        {review.status === 'failed' && (
          <div className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <strong>错误:</strong> {review.error_detail || review.error_code || '未知错误'}
          </div>
        )}
      </div>

      {/* Main content: file tree + comments */}
      {review.comments.length > 0 && (
        <div className="flex flex-col gap-6 md:flex-row">
          {/* Sidebar: File tree */}
          <div className="w-full md:w-64 flex-shrink-0">
            <FileTree
              files={review.files}
              comments={review.comments}
              activeFile={activeFile}
              onFileSelect={setActiveFile}
            />
          </div>

          {/* Comments by file */}
          <div className="flex-1 space-y-8">
            {filteredFiles.map((filePath) => {
              const fileComments = commentsByFile[filePath] ?? [];
              if (fileComments.length === 0) return null;
              return (
                <div key={filePath} id={`file-${filePath}`}>
                  <h3 className="mb-3 text-sm font-semibold text-gray-700">
                    {filePath}
                  </h3>
                  <div className="space-y-3">
                    {fileComments.map((comment) => (
                      <CommentCard key={comment.id} comment={comment} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {review.comments.length === 0 && review.status === 'completed' && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-8 text-center">
          <div className="mb-2 text-4xl">✅</div>
          <h3 className="text-lg font-medium text-green-800">没有发现代码问题</h3>
          <p className="text-sm text-green-600">变更质量良好</p>
        </div>
      )}
    </div>
  );
}

function StatItem({ label, value, color = 'text-gray-700' }: { label: string; value: number; color?: string }) {
  return (
    <div className="text-center">
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}
