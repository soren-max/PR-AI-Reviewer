# Roadmap

This roadmap controls project scope. Do not introduce future-stage modules before the current stage is accepted.

## Stage 0: Repository and Workflow Foundation

Goal:
Make the repository work like a real engineering team project.

Deliverables:

- Enterprise README.
- CONTRIBUTING guide.
- PR template.
- Issue templates.
- Development workflow documentation.
- CI workflow.
- Conventional Commits.
- PR-only development policy.

Status:
In progress.

## Stage 1: MVP Baseline

Goal:
Users can submit a GitHub PR and receive an AI-generated review result.

Deliverables:

- GitHub PR URL parsing.
- GitHub PR metadata fetching.
- GitHub diff fetching.
- FastAPI backend.
- DeepSeek review integration.
- Frontend submission and report display.

Status:
Done.

## Stage 2: Structured AI PR Review

Goal:
Move from "LLM response display" to a structured PR review tool.

Required scope:

- Diff Analysis.
- Risk Detection.
- Review Prompt V2.
- JSON structured output.
- pytest.
- Mock Test.
- GitHub Actions CI.

Forbidden in this stage:

- LangGraph.
- Tree-sitter.
- RAG.
- MCP.
- Harness.

Status:
Done, pending user acceptance and commit.

Exit criteria:

- Backend tests pass.
- GitHub and LLM calls are mocked in tests.
- Review output is normalized into structured JSON.
- CI runs on pull requests.
- Main branch remains runnable.
- Week2 score is at least 80/100.

## Stage 3: Context Quality and Schema Hardening

Goal:
Improve review accuracy and maintainability without prematurely adding full RAG or agent orchestration.

Candidate PRs:

- Add strict Pydantic Review JSON validation.
- Migrate or archive legacy root modules.
- Define code context retrieval schema and boundaries.
- Add changed-line issue validation.
- Add frontend contract tests.
- Add provider fallback and cost tracking.

Not yet allowed by default:

- Full LangGraph orchestration.
- Full Code RAG.
- Large-scale vector database integration.

Entry condition:
Stage 2 must be accepted and committed.

## Stage 4: Code Context Retrieval

Goal:
Give the reviewer enough repository context to reduce false positives and false negatives.

Deliverables:

- Repository file selection strategy.
- Changed-file neighbor context.
- Import/dependency context.
- Context budget management.
- Evaluation cases for context usefulness.

Possible technologies:

- Tree-sitter for language-aware parsing.
- Lightweight retrieval before vector search.
- FAISS only when retrieval quality can be measured.

## Stage 5: Agentic Review Workflow

Goal:
Introduce multi-step review planning only after service APIs and context retrieval are stable.

Deliverables:

- Review planning.
- Specialized review passes for security, performance, tests, and architecture.
- Result aggregation and deduplication.
- Regression evaluation for AI review quality.

Possible technologies:

- LangGraph.
- Harness-style evaluation.
- MCP integrations for developer tools.

## Stage 6: Enterprise Readiness

Goal:
Make the platform production-ready for team usage.

Deliverables:

- PostgreSQL production persistence.
- Redis queue and worker reliability.
- GitHub App authentication.
- Permission and audit model.
- Observability dashboards.
- Secret rotation and deployment hardening.
- Frontend automated tests.
- Review quality metrics.

## Current PR Plan

Issue 1:
Title: Build deterministic diff analysis
Branch: `feature/diff-analysis`
PR title: `feat(diff): add deterministic diff analysis`

Issue 2:
Title: Add risk detection engine
Branch: `feature/risk-detection`
PR title: `feat(review): add risk detection engine`

Issue 3:
Title: Upgrade Review Prompt V2
Branch: `feature/review-prompt-v2`
PR title: `feat(prompt): add review prompt v2`

Issue 4:
Title: Normalize AI review JSON output
Branch: `feature/review-json-output`
PR title: `feat(review): normalize review json output`

Issue 5:
Title: Add backend pytest and mock coverage
Branch: `test/review-service`
PR title: `test(review): add backend review service coverage`

Issue 6:
Title: Add GitHub Actions test workflow
Branch: `ci/github-actions`
PR title: `ci(actions): add backend test workflow`
