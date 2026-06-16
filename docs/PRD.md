# Product Requirements Document

## Product Name

AI PR Review Platform

## Mission

Build an enterprise-grade AI Code Review Platform that helps engineering teams review GitHub Pull Requests faster and with higher quality.

The platform is not intended to replace human reviewers. It provides a reliable AI-assisted first pass that summarizes changes, detects risk, and generates actionable review suggestions before maintainers spend focused review time.

## Target Users

- Backend engineers reviewing service and API changes.
- Frontend engineers reviewing UI and API contract changes.
- Tech leads reviewing architecture, risk, and maintainability.
- QA engineers validating regression risk.
- Engineering managers who need review quality and delivery visibility.

## User Problems

1. Large PRs are slow to review.
2. Review quality varies across reviewers.
3. Risky changes in auth, data access, config, dependencies, and error handling are easy to miss.
4. LLM review output is often unstructured and hard to render or test.
5. AI review systems often produce vague comments, false positives, or findings unrelated to changed lines.

## Product Goals

- Fetch GitHub PR metadata and code changes reliably.
- Analyze diffs and changed modules before LLM review.
- Detect deterministic risk signals.
- Generate structured AI review output.
- Reduce false positives by focusing on changed code.
- Reduce false negatives by using deterministic risk context.
- Keep latency acceptable for normal PRs.
- Keep architecture extensible for future code context retrieval and agent workflows.

## Current Stage

MVP to structured AI PR Review tool.

Required capabilities:

- Diff Analysis
- Risk Detection
- Review Prompt V2
- JSON structured output
- pytest
- Mock Test
- GitHub Actions CI

## Core User Flow

1. User submits a GitHub Pull Request URL.
2. System validates the URL.
3. System fetches PR metadata, body, changed files, and diff.
4. System performs deterministic diff analysis.
5. System performs deterministic risk detection.
6. System builds Review Prompt V2 with bounded context.
7. LLM provider generates review JSON.
8. System normalizes the response into the internal Review JSON Schema.
9. Frontend renders summary, score, risks, and review suggestions.

## Functional Requirements

### PR Input

- Accept GitHub PR URLs.
- Reject invalid or unsupported URLs with clear error responses.
- Extract owner, repository, and pull request number.

### GitHub Integration

- Fetch PR title, body, author, source branch, target branch, and metadata.
- Fetch all changed files using pagination.
- Normalize file status values.
- Handle GitHub API failures, not found, auth failures, rate limits, and network errors.

### Diff Analysis

- Parse unified diff.
- Identify changed files and hunks.
- Track additions, deletions, deleted files, and high-volume changes.
- Provide normalized change context to risk analysis and prompt construction.

### Risk Detection

- Detect high-risk files and patterns.
- Prioritize security, auth, database, config, dependency, deletion, and error-handling changes.
- Pass deterministic risk context to LLM review.

### AI Review

- Use Review Prompt V2.
- Include PR title, PR body, changed files, bounded diff content, and risk context.
- Require JSON-only output.
- Prefer actionable findings on changed code.
- Avoid speculative comments.

### Review Output

- Produce PR summary.
- Produce changed module summary.
- Produce risk-aware review issues.
- Include severity, category, file path, line range, issue body, suggestion, and optional code snippet.
- Normalize output into internal Review JSON Schema.

### Frontend

- Submit PR URL.
- Display review status.
- Display structured review result.
- Show frontend screenshots or demo notes for UI PRs.

## Non-Goals For Current Stage

- Do not introduce LangGraph.
- Do not introduce Tree-sitter.
- Do not introduce Code RAG or FAISS.
- Do not introduce MCP.
- Do not introduce Harness.
- Do not add enterprise auth or billing.
- Do not expand scope before current review quality and CI are stable.

## Quality Requirements

- Backend tests must not call real GitHub or real LLM APIs.
- CI must run on pull requests.
- Every PR must include tests or explain why tests are not applicable.
- Large diffs must be bounded or explicitly truncated.
- API errors must not expose stack traces or secrets.
- Logs must contain operational context without leaking tokens or proprietary code.

## Success Metrics

- Backend test suite passes.
- GitHub API behavior is covered by mock tests.
- LLM provider behavior is covered by mock tests.
- Review output is structured and renderable.
- `main` remains runnable after every merge.
- Week2 completion score is at least 80/100.

## Future Direction

After this stage is accepted:

- Add strict Pydantic validation for Review JSON.
- Clean up legacy root modules.
- Design code context retrieval before adding Tree-sitter or RAG.
- Add frontend tests.
- Add provider fallback and cost tracking.
- Add observability and production deployment hardening.
