# Changelog

## Unreleased

### Added

- Added a LangGraph-powered review workflow with `ReviewState`, single-purpose nodes, conditional error recovery, retry support, and a reserved checkpoint interface.
- Added workflow node, integration, API compatibility, and mocked GitHub/LLM tests.
- Added LangGraph workflow documentation and updated architecture and roadmap docs.

### Changed

- Kept `ReviewService` as a backwards-compatible facade while delegating orchestration to `WorkflowService`.
