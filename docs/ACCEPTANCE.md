# Acceptance Criteria — AI PR Review Platform

Each feature is defined by acceptance criteria before implementation begins.
All criteria must be verifiable, testable, and reproducible.

---

## F1: PR URL Parser ✅

**Input**: `https://github.com/owner/repo/pull/123`

| # | Criterion | Status |
|---|---|---|
| 1.1 | Extract owner correctly | ✅ |
| 1.2 | Extract repo correctly | ✅ |
| 1.3 | Extract pull_number correctly | ✅ |
| 1.4 | Handle trailing slash | ✅ |
| 1.5 | Handle query parameters | ✅ |
| 1.6 | Handle fragments | ✅ |
| 1.7 | Reject non-GitHub URLs | ✅ |
| 1.8 | Reject non-PR paths | ✅ |
| 1.9 | Reject non-numeric PR numbers | ✅ |
| 1.10 | Support www subdomain | ✅ |

---

## F2: GitHub API Client ✅

| # | Criterion | Status |
|---|---|---|
| 2.1 | Fetch PR metadata (title, description, author, branches) | ✅ |
| 2.2 | Fetch changed files with patches | ✅ |
| 2.3 | Auto-pagination for >100 files | ✅ |
| 2.4 | Handle HTTP 401 → GitHubAuthError | ✅ |
| 2.5 | Handle HTTP 404 → GitHubNotFoundError | ✅ |
| 2.6 | Handle HTTP 403/429 → GitHubRateLimitError | ✅ |
| 2.7 | Handle HTTP 5xx → retry with exponential backoff | ✅ |
| 2.8 | Handle network errors → GitHubConnectionError | ✅ |
| 2.9 | Track rate-limit headers | ✅ |
| 2.10 | Context manager support | ✅ |

---

## F3: Diff Analysis ✅

| # | Criterion | Status |
|---|---|---|
| 3.1 | Parse file paths from diff headers | ✅ |
| 3.2 | Parse hunk ranges (old/new start + count) | ✅ |
| 3.3 | Classify lines as add/delete/context | ✅ |
| 3.4 | Track line numbers for add/delete lines | ✅ |
| 3.5 | Detect Python function definitions | ✅ |
| 3.6 | Detect TypeScript function definitions | ✅ |
| 3.7 | Detect class definitions | ✅ |
| 3.8 | Classify functions as added/removed/modified | ✅ |
| 3.9 | Handle binary files | ✅ |
| 3.10 | Handle renamed files | ✅ |
| 3.11 | Handle new/deleted files | ✅ |

---

## F4: Risk Detection ✅

| # | Criterion | Status |
|---|---|---|
| 4.1 | Detect authentication changes | ✅ |
| 4.2 | Detect authorization changes | ✅ |
| 4.3 | Detect payment changes | ✅ |
| 4.4 | Detect security module changes | ✅ |
| 4.5 | Detect database changes | ✅ |
| 4.6 | Detect configuration changes | ✅ |
| 4.7 | Weighted scoring (0-150 scale) | ✅ |
| 4.8 | Risk levels: critical/high/medium/low | ✅ |
| 4.9 | Safe path detection (docs, tests, assets) | ✅ |
| 4.10 | Multiple categories compound correctly | ✅ |

---

## F5: Enterprise Review Prompt ✅

| # | Criterion | Status |
|---|---|---|
| 5.1 | JSON output format with summary, changed_modules, issues | ✅ |
| 5.2 | Severity levels: critical/major/minor/nit | ✅ |
| 5.3 | Bug dimension — 10 detection patterns | ✅ |
| 5.4 | Security dimension — CWE mapping | ✅ |
| 5.5 | Performance dimension — hot path focus | ✅ |
| 5.6 | Maintainability dimension | ✅ |
| 5.7 | False positive control — 5 "do not flag" rules | ✅ |
| 5.8 | Tone guidance — questions over commands | ✅ |
| 5.9 | Output self-checking checklist | ✅ |

---

## F6: Review Endpoint ✅

| # | Criterion | Status |
|---|---|---|
| 6.1 | `POST /api/v1/review` accepts PR URL | ✅ |
| 6.2 | Returns structured JSON with report | ✅ |
| 6.3 | Valid URL → 200 | ✅ |
| 6.4 | Invalid URL → 422 | ✅ |
| 6.5 | PR not found → 404 | ✅ |
| 6.6 | GitHub API error → 502 | ✅ |
| 6.7 | LLM error → 502 | ✅ |
| 6.8 | `POST /api/v1/review/raw` returns plain Markdown | ✅ |
| 6.9 | Request ID tracked through logs | ✅ |
| 6.10 | Timing information in response | ✅ |

---

## F7: Frontend ✅

| # | Criterion | Status |
|---|---|---|
| 7.1 | PR URL input form with validation | ✅ |
| 7.2 | Loading state during review | ✅ |
| 7.3 | Markdown report rendered as cards | ✅ |
| 7.4 | Error display for API failures | ✅ |
| 7.5 | Navigation between pages | ✅ |

---

## Summary

| Feature | Criteria | Status |
|---|---|---|
| F1 — PR URL Parser | 10 | ✅ All passed |
| F2 — GitHub API Client | 10 | ✅ All passed |
| F3 — Diff Analysis | 11 | ✅ All passed |
| F4 — Risk Detection | 10 | ✅ All passed |
| F5 — Enterprise Review Prompt | 9 | ✅ All passed |
| F6 — Review Endpoint | 10 | ✅ All passed |
| F7 — Frontend | 5 | ✅ All passed |
| **Total** | **65** | **✅ All passed** |
