# AI PR Review Platform

AI PR Review Platform is an AI-assisted Pull Request review system for engineering teams. Given a GitHub Pull Request URL, the platform fetches PR metadata and diffs, performs deterministic diff and risk analysis, and generates structured AI review suggestions.

The project is evolving from MVP to an enterprise-grade AI Code Review Platform. The current focus is not adding flashy features, but building a reliable engineering foundation for accurate, testable, and maintainable AI review workflows.

## Background

Modern code review is slow, inconsistent, and often overloaded by large PRs. Human reviewers still own final approval, but an AI review assistant can improve review quality by:

- Summarizing the PR intent and changed modules.
- Detecting high-risk code changes before manual review.
- Producing actionable review suggestions with file and line context.
- Reducing repeated review effort for common quality, security, and maintainability problems.
- Giving teams a consistent baseline before senior reviewers spend attention.

This project is designed as a real engineering product, not a demo. Every milestone must preserve testability, clear architecture boundaries, and a working `main` branch.

## Core Features

| Capability | Description | Status |
| --- | --- | --- |
| GitHub PR input | Parse and validate GitHub PR URLs. | Done |
| GitHub PR fetch | Fetch PR metadata, body, changed files, and unified diff. | Done |
| Diff Analysis | Normalize changed files and changed hunks for review. | Done |
| Risk Detection | Detect deterministic risk signals before LLM analysis. | Done |
| Review Prompt V2 | Use structured prompt contract for PR summary, risks, and issues. | Done |
| JSON output | Normalize AI output into stable review JSON. | Done |
| FastAPI backend | Expose review APIs and background review workflow. | Done |
| Next.js frontend | Submit PR URL and render review status/report. | MVP |
| Tests | Backend API/service/task tests with mocked GitHub and LLM calls. | Done |
| GitHub Actions CI | Run backend lint, compile, pytest, and selected legacy checks. | Done |

## System Architecture

```text
GitHub PR URL
    |
    v
Next.js Frontend
    |
    v
FastAPI Backend
    |
    +-- GitHubService
    |      +-- PR metadata
    |      +-- changed files
    |      +-- unified diff
    |
    +-- Diff Analyzer
    |      +-- changed modules
    |      +-- file stats
    |
    +-- Risk Analyzer
    |      +-- security/config/db/dependency signals
    |
    +-- LLM Provider
    |      +-- DeepSeek
    |      +-- OpenAI
    |      +-- Qwen
    |
    +-- Report Generator
           +-- Review JSON
           +-- Markdown summary
```

Backend structure:

```text
ai-pr-review/backend/app/
├── api/          # FastAPI routes and dependency wiring
├── core/         # config, database, logging, exceptions
├── models/       # persistence models
├── schemas/      # Pydantic request/response schemas
├── services/     # GitHub, LLM, review, report logic
├── tasks/        # background review orchestration
└── main.py       # application assembly
```

## Tech Stack

- Backend: FastAPI, Pydantic, SQLAlchemy async, SQLite for MVP
- Frontend: Next.js, React, TypeScript, Tailwind CSS
- AI providers: DeepSeek, OpenAI, Qwen-compatible clients
- Testing: pytest, pytest-asyncio, httpx ASGITransport, mocked providers
- Quality: Ruff, compileall, GitHub Actions
- Deployment baseline: Docker, Docker Compose

Future stages may introduce PostgreSQL, Redis, Tree-sitter, Code RAG, FAISS, LangGraph, Harness, and MCP only after the current milestone is accepted.

## Quick Start

### Backend

```bash
cd ai-pr-review/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open the API docs:

```text
http://localhost:8000/docs
```

### Frontend

```bash
cd ai-pr-review/frontend
npm install
npm run dev
```

Open the frontend:

```text
http://localhost:3000
```

### Docker Compose

```bash
cd ai-pr-review
docker compose -f infra/docker-compose.yml up --build
```

## Environment Variables

Backend `.env` is loaded from `ai-pr-review/backend/.env`.

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | No | Defaults to local SQLite database. |
| `GITHUB_TOKEN` | Recommended | GitHub token for higher API rate limits. |
| `GITHUB_API_BASE` | No | Defaults to `https://api.github.com`. |
| `LLM_PROVIDER` | No | `deepseek`, `openai`, or `qwen`. Defaults to `deepseek`. |
| `DEEPSEEK_API_KEY` | If using DeepSeek | DeepSeek API key. |
| `OPENAI_API_KEY` | If using OpenAI | OpenAI API key. |
| `QWEN_API_KEY` | If using Qwen | Qwen-compatible API key. |
| `MAX_DIFF_SIZE_BYTES` | No | Max diff characters sent to prompt context. |
| `MAX_FILES_PER_REVIEW` | No | Max files included in one review prompt. |
| `MAX_COMMENTS_PER_REVIEW` | No | Max persisted/generated review comments. |

Never commit `.env`, API keys, GitHub tokens, raw provider responses with secrets, or proprietary code snippets.

## API Examples

Create an async review:

```bash
curl -X POST http://localhost:8000/api/v1/reviews \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/42"}'
```

Fetch review result:

```bash
curl http://localhost:8000/api/v1/reviews/{review_id}
```

Run synchronous review for development/testing:

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/42"}'
```

Expected review JSON shape:

```json
{
  "overall_score": 85,
  "summary": {
    "overview": "Short PR summary",
    "total_issues": 2,
    "critical_count": 0,
    "major_count": 1,
    "minor_count": 1,
    "info_count": 0
  },
  "changed_modules": ["backend review service"],
  "issues": [
    {
      "file_path": "app/services/review_service.py",
      "line_start": 42,
      "line_end": 45,
      "severity": "major",
      "category": "bug",
      "title": "Missing error handling",
      "body": "Explain why this can fail.",
      "suggestion": "Add explicit exception handling.",
      "code_snippet": "focused snippet"
    }
  ]
}
```

## Development Workflow

All business code must be developed through Pull Requests.

1. Create or select a GitHub Issue.
2. Create a short-lived branch from `main`.
3. Implement one focused change.
4. Add or update tests.
5. Run local verification.
6. Open a Pull Request with the required template sections.
7. Wait for CI and review.
8. Merge only after checks pass and the branch is approved.

Direct business-code commits to `main` are prohibited. After every merge, `main` must remain runnable.

## PR Rules

- Every PR does exactly one thing.
- Large work must be split into multiple 1-2 day PRs.
- Every PR must include title, description, implementation approach, tests, risk impact, and screenshots or demo notes for frontend changes.
- Every PR must pass tests before merge.
- PR titles should follow Conventional Commits.

Examples:

```text
feat(review): add risk detection engine
test(diff): add unit tests for diff parser
docs(readme): update project roadmap
ci(actions): add backend test workflow
```

## Testing

Backend:

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

Frontend:

```bash
cd ai-pr-review/frontend
npm run typecheck
npm run lint
```

Current known gap:
frontend unit/component tests are not yet part of CI.

## Roadmap

Current stage: MVP to structured AI PR Review tool.

- Week2: Diff Analysis, Risk Detection, Review Prompt V2, JSON output, pytest, mock tests, GitHub Actions CI.
- Week3: Code context retrieval design, schema enforcement, duplicate module cleanup.
- Later: Tree-sitter, Code RAG, LangGraph orchestration, evaluation harness, PostgreSQL, Redis queue, GitHub App authentication, observability.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the detailed roadmap.

## Current Completion

| Area | Completion |
| --- | ---: |
| Feature completion | 90% |
| Engineering quality | 86% |
| Test coverage baseline | 84% |
| AI review capability | 82% |
| Overall | 86/100 |

See [PROJECT_SCORE.md](PROJECT_SCORE.md) and [docs/WEEK2_REPORT.md](docs/WEEK2_REPORT.md).

## Screenshots

Screenshots and product demos will be attached as the frontend stabilizes.

Suggested placeholders:

- PR submission page
- Review status page
- Structured review report page
- Risk issue list

## License

This project is licensed under the terms in [LICENSE](LICENSE).
