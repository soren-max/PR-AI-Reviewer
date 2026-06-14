/**
 * API request/response types.
 */

// === Request Types ===

export interface ReviewOptions {
  focus_areas?: string[];
  max_comments?: number;
  language?: 'zh' | 'en';
}

export interface CreateReviewReq {
  pr_url: string;
  options?: ReviewOptions;
}

// === Response Types ===

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  request_id?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

// === API Client Config ===

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api/v1';
