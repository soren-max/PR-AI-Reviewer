# Development Workflow

This document defines how AI PR Review Platform work moves from idea to merged code.

## Workflow Overview

```text
Issue
  -> Branch
  -> Commit
  -> Pull Request
  -> CI
  -> Review
  -> Merge
  -> Runnable main
```

Recommended collaboration rhythm:

```text
Reasonix: requirement analysis + task breakdown + first implementation
Codex: code review + architecture hardening + tests + refactor
User: acceptance + git commit + merge
Next iteration
```

## Main Branch Policy

- `main` is always expected to be runnable.
- Direct business-code commits to `main` are prohibited.
- All feature, fix, refactor, test, and CI changes must go through PR.
- Documentation-only fixes may still use PR for traceability.
- Broken `main` is treated as a P0 engineering issue.

## Issue Policy

Use an Issue before starting non-trivial work.

Each Issue should include:

- Title.
- Problem or goal.
- Scope.
- Non-goals.
- Acceptance criteria.
- Suggested branch name.
- Suggested PR title.
- Test plan.

## Branch Policy

Branch naming:

```text
feature/<short-name>
fix/<short-name>
test/<short-name>
refactor/<short-name>
docs/<short-name>
ci/<short-name>
```

Examples:

```text
feature/pr-url-parser
feature/github-client
feature/diff-analysis
feature/risk-detection
feature/review-json-output
test/review-service
ci/github-actions
```

## Pull Request Policy

Every PR must:

- Do exactly one thing.
- Be reviewable in one sitting.
- Be scoped to 1-2 days of implementation work.
- Include implementation notes.
- Include tests or a clear reason tests do not apply.
- Include risk impact.
- Include screenshots or demo notes for frontend work.
- Pass CI before merge.

Large features must be split into a sequence of small PRs.

## Commit Policy

Use Conventional Commits:

```text
feat(review): add risk detection engine
test(diff): add unit tests for diff parser
docs(readme): update project roadmap
fix(github): handle paginated PR files
refactor(review): isolate report generator
ci(actions): add backend test workflow
chore(repo): add issue templates
```

Allowed types:

- `feat`
- `fix`
- `docs`
- `test`
- `refactor`
- `chore`
- `ci`

## Required Checks

Backend:

```bash
cd ai-pr-review/backend
python -m ruff check app tests
python -m compileall app
python -m pytest -q
```

Legacy selected:

```bash
python3 -m pytest \
  tests/test_parser.py \
  tests/test_github_client.py \
  tests/test_diff_analyzer.py \
  tests/test_risk_engine.py \
  -q
```

Frontend:

```bash
cd ai-pr-review/frontend
npm run typecheck
npm run lint
```

## Current Stage PR Plan

Current stage:
MVP to structured AI PR Review tool.

### Issue 1

Title:
Build deterministic diff analysis

Goal:
Normalize changed files and hunks so review logic can reason about the PR before calling the model.

Acceptance criteria:

- Unified diff parsing is deterministic.
- Changed files and hunks are represented consistently.
- Deleted files and large changes are handled.
- Unit tests cover parser behavior.

Branch:
`feature/diff-analysis`

PR:
Title:
`feat(diff): add deterministic diff analysis`

Feature description:
Add deterministic diff parsing for changed files and hunks.

Implementation approach:
Keep parsing logic in the backend review domain and expose normalized data to risk analysis and prompt building.

Test method:
Run backend pytest and legacy diff tests.

Commit example:
`feat(diff): add deterministic diff analysis`

### Issue 2

Title:
Add risk detection engine

Goal:
Detect high-risk PR changes before LLM review.

Acceptance criteria:

- Detect auth, security, database, config, dependency, deletion, and error-handling risk signals.
- Risk context is passed into Review Prompt V2.
- Tests cover representative risk patterns.

Branch:
`feature/risk-detection`

PR:
Title:
`feat(review): add risk detection engine`

Feature description:
Add deterministic risk detection to guide model attention.

Implementation approach:
Analyze normalized diff metadata and generate bounded risk context.

Test method:
Run backend service tests and risk engine tests.

Commit example:
`feat(review): add risk detection engine`

### Issue 3

Title:
Upgrade Review Prompt V2

Goal:
Improve review accuracy and enforce a stable output contract.

Acceptance criteria:

- Prompt includes PR title, PR body, changed files, diff, and risk context.
- Prompt requires JSON-only output.
- Prompt discourages speculative findings.
- Prompt asks for actionable issues tied to changed code.

Branch:
`feature/review-prompt-v2`

PR:
Title:
`feat(prompt): add review prompt v2`

Feature description:
Upgrade prompt for structured PR review.

Implementation approach:
Update prompt contract and prompt builder tests.

Test method:
Run prompt and LLM service tests.

Commit example:
`feat(prompt): add review prompt v2`

### Issue 4

Title:
Normalize AI review JSON output

Goal:
Make AI review output predictable for API and frontend rendering.

Acceptance criteria:

- Output includes summary, changed modules, issues, and score.
- Issues include severity, category, file path, line range, body, suggestion, and optional snippet.
- Parser handles common model formatting noise.
- Tests cover valid and invalid model output.

Branch:
`feature/review-json-output`

PR:
Title:
`feat(review): normalize review json output`

Feature description:
Normalize LLM output into internal review JSON.

Implementation approach:
Parse JSON defensively and map fields to the canonical response shape.

Test method:
Run report generator and API tests.

Commit example:
`feat(review): normalize review json output`

### Issue 5

Title:
Add backend pytest and mock coverage

Goal:
Make GitHub, LLM, API, and background task behavior testable without external calls.

Acceptance criteria:

- Tests do not call real GitHub or real LLM APIs.
- API tests use dependency overrides.
- Task tests mock GitHub and LLM services.
- Backend pytest passes locally.

Branch:
`test/review-service`

PR:
Title:
`test(review): add backend review service coverage`

Feature description:
Add deterministic tests for review service behavior.

Implementation approach:
Use mocks at service/provider boundaries and reset test database state per test.

Test method:
Run backend pytest.

Commit example:
`test(review): add backend review service coverage`

### Issue 6

Title:
Add GitHub Actions CI

Goal:
Enforce quality gates on pull requests.

Acceptance criteria:

- CI runs on pull requests and pushes to `main`.
- Backend CI runs Ruff, compileall, and pytest.
- Legacy selected tests run separately.
- CI uses dummy API keys and never calls real external services.

Branch:
`ci/github-actions`

PR:
Title:
`ci(actions): add backend test workflow`

Feature description:
Add GitHub Actions workflow for backend and legacy checks.

Implementation approach:
Use separate jobs for backend and legacy checks.

Test method:
Open PR and verify CI passes.

Commit example:
`ci(actions): add backend test workflow`

## Merge Policy

Before merge:

- PR is approved.
- CI is green.
- Required tests are documented.
- Risk is acceptable.

After merge:

- Pull latest `main`.
- Run smoke checks if the PR touched runtime behavior.
- Create follow-up issues for known remaining debt.
