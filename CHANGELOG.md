# Changelog

## Unreleased

### Added

- Added Tree-sitter parser foundation with `ParserFactory`, `TreeSitterService`, Python AST output, and reserved Java/Go/TypeScript extension points.
- Added Tree-sitter parser pytest coverage for Python parsing, syntax error ASTs, reserved languages, and unsupported languages.
- Added Sprint 3 Review and Retrospective documentation for final acceptance, Definition of Done, technical debt, and Sprint 4 readiness.
- Added review workflow observability metrics for review time, workflow latency, GitHub API latency, LLM latency, prompt length, token usage, risk score, and node latency.
- Added frontend metrics display for Review Time, Prompt Tokens, Completion Tokens, and Risk Score.
- Added metrics unit, workflow, and API tests with mocked GitHub/LLM boundaries.
- Added a LangGraph-powered review workflow with `ReviewState`, single-purpose nodes, conditional error recovery, retry support, and a reserved checkpoint interface.
- Added workflow node, integration, API compatibility, and mocked GitHub/LLM tests.
- Added LangGraph workflow documentation and updated architecture and roadmap docs.

### Changed

- Changed `app.services.review.prompt_builder` into a compatibility wrapper around the canonical LLM prompt builder to remove divergent prompt logic.
- Kept `ReviewService` as a backwards-compatible facade while delegating orchestration to `WorkflowService`.
