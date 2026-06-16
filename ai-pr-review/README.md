# AI PR Review

> AI-powered Pull Request code review platform — MVP v0.1.0

Submit a GitHub PR URL and get an automated, structured code review powered by DeepSeek V4 Pro.

## Features

- 🔗 **PR URL input** — paste any public GitHub PR link
- 🔍 **Automatic diff extraction** — fetches PR metadata and unified diffs via GitHub API
- 🤖 **LLM-powered analysis** — DeepSeek V4 Pro evaluates code quality, security, performance, and best practices
- 🧭 **LangGraph workflow** — stateful review orchestration with retries, conditional error recovery, and future checkpoint extension
- 📈 **Review observability** — exposes review time, GitHub/LLM latency, prompt/token usage, and risk metrics
- 📊 **Structured report** — score gauge, severity-categorized issues, code suggestions, file tree navigation
- ⚡ **Async processing** — non-blocking; poll status while review runs in background
- 📜 **History** — review records persisted for future reference

## Architecture

```
ai-pr-review/
├── backend/        # Python FastAPI (async, SQLAlchemy, SQLite)
├── frontend/       # Next.js 14 (App Router, TypeScript, Tailwind)
├── infra/          # Docker Compose (dev + prod)
├── docs/           # ADRs, API specs
└── scripts/        # Bootstrap, test runner
```

See [docs/architecture.md](docs/architecture.md) for the full architecture design.
The synchronous review path is now orchestrated by LangGraph while preserving the existing API response contract. Completed synchronous reviews also include an additive `metrics` object for review time, workflow latency, token usage, prompt length, and risk score.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (optional, for containerized setup)

### 1. Clone & Bootstrap

```bash
cd ai-pr-review
make install          # or: ./scripts/bootstrap.sh
```

### 2. Set Environment Variables

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set DEEPSEEK_API_KEY (required)
# Optionally set GITHUB_TOKEN for higher API rate limits
```

### 3. Start Development

```bash
# Option A: Local development (two terminals)
make backend-dev    # Terminal 1 — FastAPI on :8000
make frontend-dev   # Terminal 2 — Next.js on :3000

# Option B: Docker Compose
make docker-up      # Both services in containers
```

### 4. Use the App

Open **http://localhost:3000** → paste a PR URL → review!

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/reviews` | Submit a new PR review |
| `POST` | `/api/v1/review` | Synchronously review a PR via the LangGraph workflow |
| `POST` | `/api/v1/review/raw` | Return the synchronous review report as Markdown |
| `GET` | `/api/v1/reviews` | List all reviews (paginated) |
| `GET` | `/api/v1/reviews/{id}` | Get review details |
| `GET` | `/api/v1/health` | Health check |

Full API spec at [docs/api-spec.yaml](docs/api-spec.yaml) or at `/docs` when the backend is running.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek V4 Pro API key |
| `GITHUB_TOKEN` | ❌ | — | GitHub token (60 req/h without it) |
| `DATABASE_URL` | ❌ | `sqlite+aiosqlite:///./data/reviews.db` | Database connection string |
| `DEEPSEEK_MODEL` | ❌ | `deepseek-chat` | Model name |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000/api/v1` | Backend API base URL |

## Development

```bash
make lint           # Lint all code (ruff + eslint)
make typecheck      # Type check (mypy + tsc)
make test           # Run backend tests
make ci             # Full CI pipeline (lint + typecheck + test)
```

## Project Structure

```
ai-pr-review/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes (v1)
│   │   ├── core/         # Config, DB, exceptions, logging
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic (GitHub, LLM, Analyzer, Report)
│   │   ├── tasks/        # Async task orchestration
│   │   └── main.py       # FastAPI app entry
│   ├── tests/            # pytest test suite
│   └── alembic/          # Database migrations
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js App Router pages
│   │   ├── components/   # React components
│   │   ├── lib/          # API client, utils, constants
│   │   └── types/        # TypeScript type definitions
│   └── Dockerfile
├── infra/                # Docker Compose configs
└── docs/                 # Architecture & design docs
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), SQLite |
| Workflow | LangGraph |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| AI | DeepSeek V4 Pro API |
| Infra | Docker, Docker Compose |

## License

MIT
