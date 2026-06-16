# Acceptance Criteria

This document defines what must be true before a feature, PR, milestone, or release is considered done.

## Repository Acceptance

- README explains product purpose, architecture, setup, API usage, tests, roadmap, PR rules, and license.
- CONTRIBUTING explains branch naming, PR rules, Conventional Commits, tests, and Definition of Done.
- PR template requires title, description, implementation approach, tests, risk, and screenshots/demo notes for frontend changes.
- Issue templates exist for feature requests and bug reports.
- CI runs on pull requests and pushes to `main`.
- Business code is not committed directly to `main`.

## Pull Request Acceptance

Every PR must satisfy:

- The PR does one thing.
- The PR is small enough to complete in 1-2 days.
- The PR links to an Issue when applicable.
- The PR title follows Conventional Commits.
- The PR description includes:
  - Functional description.
  - Implementation approach.
  - Test method and result.
  - Risk impact.
  - Screenshots or demo notes for frontend changes.
- Tests pass before merge.
- Main branch remains runnable after merge.

## Backend Acceptance

- API routes are thin and delegate business logic to services.
- Public request/response contracts use Pydantic schemas.
- GitHub API calls are behind service classes.
- LLM calls are behind provider classes.
- Exceptions are handled without leaking stack traces to API clients.
- Logs include useful context without leaking secrets, tokens, or proprietary full prompts.
- Environment variables are validated through settings.

## AI Review Acceptance

- Prompt includes PR title, PR body, bounded diff, changed files, and deterministic risk context.
- Large diffs are truncated or chunked explicitly.
- Output follows the Review JSON Schema.
- Review issues include severity, category, file path, line range, issue body, and suggestion.
- Review suggestions focus on changed code.
- Risk detection covers security, auth, database, config, dependency, deletion, and error-handling changes.
- Model output is parsed defensively.

## Testing Acceptance

- Unit tests cover deterministic parsing and risk logic.
- Mock tests cover GitHub API behavior.
- Mock tests cover LLM provider behavior.
- API tests use dependency overrides and do not call external services.
- Background task tests mock GitHub and LLM services.
- CI runs backend lint, compile, and pytest.
- Frontend changes must run typecheck and lint until frontend test framework is added.

## Current Stage Acceptance

Stage:
MVP to structured AI PR Review tool.

Required:

- Diff Analysis: Done.
- Risk Detection: Done.
- Review Prompt V2: Done.
- JSON structured output: Done.
- pytest: Done.
- Mock Test: Done.
- GitHub Actions CI: Done.

Evidence:

- Backend pytest: `77 passed`.
- Legacy selected pytest: `146 passed`.
- Backend Ruff: passed.
- Backend compile: passed.

## Done Definition

A task is done only when:

- Code or docs are implemented.
- Tests are added or updated when needed.
- Relevant checks pass.
- Documentation is updated for workflow, API, architecture, or behavior changes.
- Remaining risks are documented.
- The user can accept, commit, and merge without breaking `main`.
