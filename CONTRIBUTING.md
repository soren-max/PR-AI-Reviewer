# Contributing to AI PR Review Platform

Thank you for contributing. This document defines the development workflow, PR standards, and commit conventions for the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Workflow](#development-workflow)
- [Branch Strategy](#branch-strategy)
- [Commit Convention](#commit-convention)
- [Pull Request Standards](#pull-request-standards)
- [PR Review Checklist](#pr-review-checklist)
- [Testing Requirements](#testing-requirements)
- [Getting Help](#getting-help)

## Code of Conduct

All contributors must follow the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Development Workflow

```text
Issue → Branch → Commit → PR → CI → Review → Merge → Runnable main
```

### 1. Pick or Create an Issue

- Find an existing issue or create a new one using the templates in `.github/ISSUE_TEMPLATE/`
- Each issue describes one atomic unit of work
- Large features should be split into multiple linked issues

### 2. Create a Branch

```bash
git checkout -b feat/risk-engine
```

Branch naming:

| Prefix | Usage |
|---|---|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `docs/` | Documentation |
| `refactor/` | Code refactor (no behavior change) |
| `test/` | Test addition or improvement |
| `ci/` | CI / build / pipeline changes |
| `chore/` | Tooling, dependencies, config |

### 3. Commit Early, Commit Often

- Each commit should be a logical unit of change
- Use [Conventional Commits](#commit-convention)
- No single-commit PRs for large features — show your work

### 4. Open a Pull Request

- Fill out the PR template completely
- Link to the issue(s) it resolves
- Request review from at least one maintainer

### 5. CI Must Pass

- Lint, type-check, and test jobs must all pass
- Coverage must meet the ≥80% threshold

### 6. Review and Merge

- At least one maintainer approval required
- Squash merge recommended for clean history
- Delete the branch after merge

## Branch Strategy

```
main           ← Production-ready.  Always runnable.
  │
  ├── feat/*   ← Feature branches.  Short-lived.
  ├── fix/*    ← Bug fixes.
  ├── docs/*   ← Doc-only changes.
  └── refactor/* ← Cleanup refactors.
```

**Rules**:

1. **No direct commits to `main`** for business logic
2. All changes merge via PR
3. `main` must pass CI at all times
4. Feature branches rebase on `main` before merge

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) with scoped prefixes.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Usage | Example |
|---|---|---|
| `feat` | New feature | `feat(review): add risk detection engine` |
| `fix` | Bug fix | `fix(github): handle paginated API responses` |
| `docs` | Documentation | `docs(readme): update API reference` |
| `test` | Test addition/update | `test(parser): add URL validation edge cases` |
| `refactor` | Code refactor | `refactor(service): extract prompt builder module` |
| `ci` | CI configuration | `ci: add coverage threshold to test workflow` |
| `chore` | Tooling, deps | `chore: upgrade fastapi to 0.115` |

### Scopes

| Scope | Module |
|---|---|
| `github` | github/parser, github/client |
| `review` | review/diff_parser, backend review service |
| `risk` | risk/engine |
| `prompt` | prompts/, prompt builder |
| `api` | FastAPI routes |
| `frontend` | Next.js frontend |
| `docs` | Documentation |
| `ci` | GitHub Actions |
| `test` | Test suite |

### Examples

```
feat(risk): add authentication and payment risk categories

- Added RiskCategory dataclass with weight and patterns
- Implemented 8 predefined risk categories
- Added assess_risk() with file path pattern matching
- Closes #12
```

```
fix(github): handle 404 for deleted repositories

When a PR references a deleted or private repository,
the GitHub API returns 404.  Previously this crashed the
parser; now it raises PRNotFoundError with a clear message.
```

```
docs(readme): add architecture diagram and quick start
```

## Pull Request Standards

### 1. Each PR Does ONE Thing

- One feature, one fix, one refactor = one PR
- Split large features: `feat/context-retrieval-part-1`, `feat/context-retrieval-part-2`

### 2. PR Title Convention

Follow the same format as commit messages:

```
feat(review): add context retrieval system
fix(risk): correct false positive for migration files
```

### 3. PR Description Template

Every PR must include:

```markdown
## Summary
One-line description of the change.

## Motivation
Why this change is needed.  Link to the issue.

## Implementation Approach
Brief explanation of the technical approach.

## Testing
How was this tested?  Include test commands.

## Risk Assessment
What could go wrong?  Are there rollback considerations?

## Screenshots
If the change affects the UI, include before/after screenshots.
```

### 4. PR Size Guidelines

| Size | Lines Changed | Recommended |
|---|---|---|
| Small | < 100 | ✅ Ideal |
| Medium | 100-500 | ✅ Fine |
| Large | 500-1000 | ⚠️ Split if possible |
| XL | > 1000 | ❌ Must be split |

### 5. Invalid PRs

The following will be rejected:

- PR with blank or template-only description
- PR that combines multiple unrelated changes
- PR that doesn't pass CI
- PR without tests for new functionality
- PR committed entirely in one push (no incremental commits)

## PR Review Checklist

Before requesting review, verify:

- [ ] Tests pass locally (`make test`)
- [ ] Lint passes (`make lint`)
- [ ] Type-check passes (`make typecheck`)
- [ ] No debug prints or commented-out code
- [ ] Documentation updated if API changed
- [ ] All acceptance criteria from the linked issue are met
- [ ] PR description is complete and accurate

## Testing Requirements

1. **New features must include tests** — minimum: happy path + error path
2. **Bug fixes must include a regression test**
3. **Coverage must not decrease** — maintain ≥80%
4. **External API calls must be mocked** — use `@patch` or `unittest.mock`

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_parser.py -v

# Run with coverage report
python -m pytest tests/ --cov --cov-report=term-missing
```

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/soren-max/PR-AI-Reviewer/discussions)
- **Bugs**: Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) template
- **Features**: Use the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) template
- **Security**: Do NOT open a public issue. Contact maintainers directly.
