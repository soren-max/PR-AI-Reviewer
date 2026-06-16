# Development Workflow

This document defines how work moves from idea to merged code.

---

## Workflow Overview

```text
Issue → Branch → Commit → PR → CI → Review → Merge → Runnable main
```

---

## 1. Issue

Every change starts with an Issue. Use the templates:

- **Bug**: [`.github/ISSUE_TEMPLATE/bug_report.md`](../.github/ISSUE_TEMPLATE/bug_report.md)
- **Feature**: [`.github/ISSUE_TEMPLATE/feature_request.md`](../.github/ISSUE_TEMPLATE/feature_request.md)

Acceptance criteria must be written **before** code.

---

## 2. Branch

```bash
git checkout -b feat/risk-engine   # feature
git checkout -b fix/github-auth    # bug fix
git checkout -b docs/readme        # documentation
```

| Prefix | Usage |
|---|---|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `docs/` | Documentation |
| `refactor/` | Refactor (no behavior change) |
| `test/` | Tests |
| `ci/` | CI/CD |
| `chore/` | Tooling, deps |

---

## 3. Commit

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat(risk): add authentication category detection"
git commit -m "fix(github): handle 429 rate limit response"
git commit -m "test(parser): add URL edge case coverage"
```

**Commit early, commit often.**  No single-commit PR for large features.

---

## 4. Pull Request

1. Push branch
2. Open PR against `main`
3. Fill out [PR template](../.github/pull_request_template.md)
4. Wait for CI (lint → test)
5. Request review

### PR Must Include

- ✅ Title follows Conventional Commits
- ✅ Description: summary + implementation + testing + risk
- ✅ All tests pass
- ✅ Coverage ≥ 80%

### PR Must NOT

- ❌ Be blank or template-only
- ❌ Mix multiple unrelated changes
- ❌ Skip tests for new functionality
- ❌ Have only one giant commit

---

## 5. CI

Automatically runs on every push and PR:

```text
Lint (ruff + flake8 + mypy) → Test (pytest --cov) → Summary
```

Failures block merge. See [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

---

## 6. Review

- At least one maintainer approval required
- Reviewer checks: correctness, style, tests, docs
- Author addresses feedback with additional commits

---

## 7. Merge

- Squash merge recommended
- Delete feature branch after merge
- `main` must remain runnable after merge

---

## Local Development Commands

```bash
make install      # Install all dependencies
make run          # Start FastAPI server
make test         # Run pytest
make lint         # Run linters
make ci           # Full local CI (lint + test)
make format       # Auto-format code
```

---

## Quality Gates

| Gate | Tool | Threshold |
|---|---|---|
| Lint | ruff, flake8, mypy | 0 errors |
| Format | ruff format | Must match |
| Tests | pytest | 100% pass |
| Coverage | pytest-cov | ≥ 80% |
