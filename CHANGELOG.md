# Changelog

## Unreleased

### Added

- Added review workflow observability metrics for review time, workflow latency, GitHub API latency, LLM latency, prompt length, token usage, risk score, and node latency.
- Added frontend metrics display for Review Time, Prompt Tokens, Completion Tokens, and Risk Score.
- Added metrics unit, workflow, and API tests with mocked GitHub/LLM boundaries.
- Added a LangGraph-powered review workflow with `ReviewState`, single-purpose nodes, conditional error recovery, retry support, and a reserved checkpoint interface.
- Added workflow node, integration, API compatibility, and mocked GitHub/LLM tests.
- Added LangGraph workflow documentation and updated architecture and roadmap docs.

### Changed

- Kept `ReviewService` as a backwards-compatible facade while delegating orchestration to `WorkflowService`.
