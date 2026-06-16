# Contributing

AI PR Review Platform follows a Pull Request based development workflow. The goal is to keep `main` runnable, keep reviews small, and make every change testable.

## Core Rules

- All new features must be developed through Pull Requests.
- Direct business-code commits to `main` are prohibited.
- Every PR must do one thing.
- Large features must be split into multiple small PRs.
- Each PR should be small enough to finish in 1-2 working days.
- Every PR must pass tests before merge.
- After every merge, `main` must remain runnable.

## Branch Naming

Use short, descriptive branch names.

Recommended patterns:

```text
feature/pr-url-parser
feature/github-client
feature/diff-analysis
feature/risk-detection
feature/review-json-output
test/review-service
ci/github-actions
docs/development-workflow
fix/github-pagination
refactor/review-service
```

## Pull Request Requirements

Every PR must include:

- Title
- Feature or bug description
- Implementation approach
- Test method and test result
- Risk impact
- Screenshot or demo notes if frontend behavior changed
- Linked Issue when applicable

PR title should follow Conventional Commits:

```text
feat(review): add risk detection engine
fix(github): paginate pull request files
test(diff): add unit tests for diff parser
docs(readme): update project roadmap
ci(actions): add backend test workflow
refactor(review): isolate report generation
chore(deps): update development dependencies
```

## Conventional Commits

Use this format:

```text
<type>(<scope>): <description>
```

Allowed types:

| Type | Meaning |
| --- | --- |
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Tests |
| `refactor` | Code refactor without behavior change |
| `chore` | Build, dependency, or repository maintenance |
| `ci` | CI configuration |

Examples:

```text
feat(review): add risk detection engine
test(diff): add unit tests for diff parser
docs(readme): update project roadmap
fix(github): handle deleted files in PR diff
refactor(llm): extract provider interface
ci(actions): run backend pytest on pull requests
chore(repo): add issue templates
```

Commit rules:

- One commit should represent one coherent change.
- Do not mix unrelated refactors with feature work.
- Include tests with code changes.
- Do not commit secrets, `.env`, local databases, caches, or generated build outputs.

## Local Development

Backend setup:

```bash
cd ai-pr-review/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend setup:

```bash
cd ai-pr-review/frontend
npm install
npm run dev
```

Docker setup:

```bash
cd ai-pr-review
docker compose -f infra/docker-compose.yml up --build
```

## Testing Rules

All behavior changes require tests.

Required test strategy:

- Pure parsing/risk logic: unit tests.
- GitHub API integration: mocked GitHub tests.
- LLM provider integration: mocked provider/client tests.
- FastAPI routes: API tests with dependency overrides.
- Background tasks: task tests with mocked GitHub and LLM services.
- Prompt changes: tests that assert required context is included and large inputs are bounded.
- Bug fixes: regression test first when practical.

Never call real GitHub or real LLM APIs in tests.

Backend checks:

```bash
cd ai-pr-review/backend
python -m ruff check app tests
python -m compileall app
python -m pytest -q
```

Legacy selected checks:

```bash
python3 -m pytest \
  tests/test_parser.py \
  tests/test_github_client.py \
  tests/test_diff_analyzer.py \
  tests/test_risk_engine.py \
  -q
```

Frontend checks:

```bash
cd ai-pr-review/frontend
npm run typecheck
npm run lint
```

## Code Standards

Follow [docs/PROJECT_RULES.md](docs/PROJECT_RULES.md).

Key expectations:

- Keep API routes thin.
- Put business orchestration in services.
- Keep provider-specific code behind provider classes.
- Prefer explicit Pydantic schemas for API contracts.
- Do not duplicate review logic across API, service, task, and frontend layers.
- Do not log secrets, API keys, authorization headers, or full proprietary diffs/prompts.
- Keep changes minimal and localized.

## Review Checklist

Before requesting review:

- [ ] The PR does one thing.
- [ ] The branch name is descriptive.
- [ ] The PR title follows Conventional Commits.
- [ ] Tests were added or updated.
- [ ] Backend checks pass if backend changed.
- [ ] Frontend checks pass if frontend changed.
- [ ] Documentation was updated if behavior or workflow changed.
- [ ] Risk impact is documented.
- [ ] No secrets or local artifacts are committed.

## Issue Workflow

Use the issue templates under `.github/ISSUE_TEMPLATE/`.

Feature issues should include:

- Problem
- Goal
- Scope
- Non-goals
- Acceptance criteria
- Suggested PR breakdown

Bug reports should include:

- Reproduction steps
- Expected behavior
- Actual behavior
- Logs or screenshots
- Environment
- Suspected impact

## Definition of Done

A task is done only when:

- Code or documentation is implemented.
- Tests are added or updated when applicable.
- Relevant checks pass.
- PR description explains implementation and risk.
- Review comments are addressed.
- `main` remains runnable after merge.
