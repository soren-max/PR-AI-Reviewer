'use client';

import { useState } from 'react';
import { SeverityBadge } from './SeverityBadge';
import { CATEGORY_LABELS } from '@/lib/constants';
import type { ReviewComment } from '@/types/review';

interface CommentCardProps {
  comment: ReviewComment;
  isExpanded?: boolean;
}

export function CommentCard({ comment, isExpanded = false }: CommentCardProps) {
  const [expanded, setExpanded] = useState(isExpanded);
  const needsToggle = comment.body.length > 200;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <SeverityBadge severity={comment.severity} />
        <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {CATEGORY_LABELS[comment.category] ?? comment.category}
        </span>
        {comment.line_start && (
          <span className="text-xs text-gray-500">
            第 {comment.line_start}{comment.line_end && comment.line_end !== comment.line_start ? `-${comment.line_end}` : ''} 行
          </span>
        )}
      </div>

      {/* Title */}
      <h4 className="mb-1 font-medium text-gray-900">{comment.title}</h4>

      {/* Body with collapse */}
      <div className="mb-2">
        <p className={`text-sm text-gray-700 ${!expanded && needsToggle ? 'line-clamp-3' : ''}`}>
          {comment.body}
        </p>
        {needsToggle && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-1 text-xs text-blue-600 hover:text-blue-800"
          >
            {expanded ? '收起' : '展开全部'}
          </button>
        )}
      </div>

      {/* Code snippet */}
      {comment.code_snippet && (
        <div className="mb-2 overflow-x-auto rounded bg-gray-50 p-3">
          <pre className="text-xs text-gray-800">
            <code>{comment.code_snippet}</code>
          </pre>
        </div>
      )}

      {/* Suggestion */}
      {comment.suggestion && (
        <div className="rounded border border-green-200 bg-green-50 p-3">
          <div className="mb-1 text-xs font-medium text-green-700">💡 改进建议</div>
          <pre className="overflow-x-auto text-xs text-green-800">
            <code>{comment.suggestion}</code>
          </pre>
        </div>
      )}

      {/* Footer: file path */}
      <div className="mt-2 text-xs text-gray-400">
        {comment.file_path}
      </div>
    </div>
  );
}
