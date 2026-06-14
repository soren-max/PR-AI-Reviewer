/**
 * Domain types for the PR Review system.
 * Aligned with backend Pydantic schemas.
 */

// === Enums ===

export const ReviewStatus = {
  PENDING: 'pending',
  FETCHING: 'fetching',
  ANALYZING: 'analyzing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

export type ReviewStatus = (typeof ReviewStatus)[keyof typeof ReviewStatus];

export const Severity = {
  CRITICAL: 'critical',
  MAJOR: 'major',
  MINOR: 'minor',
  INFO: 'info',
} as const;

export type Severity = (typeof Severity)[keyof typeof Severity];

export const Category = {
  SECURITY: 'security',
  PERFORMANCE: 'performance',
  BUG: 'bug',
  DESIGN: 'design',
  STYLE: 'style',
  BEST_PRACTICE: 'best_practice',
  READABILITY: 'readability',
} as const;

export type Category = (typeof Category)[keyof typeof Category];

// === Sync Review Types (POST /api/v1/review) ===

export interface ReviewSyncRequest {
  pr_url: string;
  language?: 'zh' | 'en';
}

export interface ReviewSyncResponse {
  pr_url: string;
  owner: string;
  repo: string;
  pull_number: number;
  pr_title: string;
  report: string;          // Markdown review report
  input_tokens: number;
  output_tokens: number;
  model: string;
}

// === Data Types ===

export interface PRInfo {
  owner: string;
  repo: string;
  number: number;
  title: string | null;
  author: string | null;
  base_branch: string | null;
  head_branch: string | null;
  changed_files_count: number;
  additions: number;
  deletions: number;
}

export interface ReviewSummary {
  overall_score: number | null;
  total_issues: number;
  critical: number;
  major: number;
  minor: number;
  info: number;
}

export interface ReviewComment {
  id: string;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  severity: Severity;
  category: Category;
  title: string;
  body: string;
  suggestion: string | null;
  code_snippet: string | null;
}

export interface ReviewFile {
  file_path: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  comments_count: number;
}

export interface Review {
  id: string;
  pr_url: string;
  status: ReviewStatus;
  created_at: string | null;
}

export interface ReviewDetail extends Review {
  pr_info: PRInfo | null;
  summary: ReviewSummary | null;
  comments: ReviewComment[];
  files: ReviewFile[];
  completed_at: string | null;
  duration_ms: number | null;
  error_code: string | null;
  error_detail: string | null;
}
