# 🤖 AI PR Review Platform

<p align="center">
  <img src="https://img.shields.io/badge/status-active-success" alt="Status"/>
  <img src="https://img.shields.io/badge/python-3.12-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js"/>
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20|%20OpenAI%20|%20Qwen-blueviolet" alt="LLM"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <a href="https://github.com/soren-max/PR-AI-Reviewer/actions/workflows/ci.yml">
    <img src="https://github.com/soren-max/PR-AI-Reviewer/actions/workflows/ci.yml/badge.svg" alt="CI"/>
  </a>
</p>

<p align="center">
  <strong>Enterprise-grade AI code review platform</strong><br>
  <em>Summarize changes · Detect risk · Generate actionable review suggestions</em>
</p>

---

## 📋 Table of Contents

- [Background](#-background)
- [Core Features](#-core-features)
- [System Architecture](#-system-architecture)
- [Technical Stack](#-technical-stack)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Development Workflow](#-development-workflow)
- [PR Standards](#-pr-standards)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [Project Status](#-project-status)
- [License](#-license)

---

## 🎯 Background

Modern code review is **slow, inconsistent, and often overloaded** by large PRs. Human reviewers own final approval, but an AI review assistant improves quality by:

- **Summarizing** PR intent and changed modules
- **Detecting** high-risk code changes before manual review
- **Producing** actionable review suggestions with file and line context
- **Reducing** repeated effort for common quality, security, and maintainability problems
- **Giving** teams a consistent baseline before senior reviewers spend focused time

This is a **real engineering product**, not a demo. Every milestone preserves testability, clear architecture boundaries, and a working `main` branch.

---

## ✨ Core Features

| Capability | Description | Status |
|---|---|---|
| 🔗 **GitHub PR Input** | Parse and validate GitHub PR URLs | ✅ Done |
| 📥 **PR Fetch** | Fetch metadata, changed files, and unified diff via GitHub API | ✅ Done |
| 🔍 **Diff Analysis** | Structured parsing of changed files, hunks, functions, and classes | ✅ Done |
| ⚠️ **Risk Detection** | 8 risk categories with weighted scoring | ✅ Done |
| 📝 **Review Prompt V2** | Enterprise JSON output format with CWE mapping and false-positive control | ✅ Done |
| 📊 **Structured Report** | JSON → Markdown report with severity-categorized issues | ✅ Done |
| 🧭 **LangGraph Workflow** | Stateful Agent Workflow orchestration with retry and error recovery | ✅ Done |
| 📈 **Review Observability** | Review time, workflow latency, GitHub/LLM latency, prompt/token usage, and risk metrics | ✅ Done |
| 🚀 **FastAPI Backend** | `POST /api/v1/review` synchronous review endpoint | ✅ Done |
| 🖥️ **Next.js Frontend** | PR URL input → report rendering | ✅ Done |
| 🔄 **Multi-LLM** | DeepSeek / OpenAI / Qwen via config switch | ✅ Done |
| 🧪 **Test Suite** | Workflow, API, parser, risk, GitHub, and LLM tests with external calls mocked | ✅ Done |
| 📋 **Acceptance Criteria** | 86 acceptance criteria across 6 features | ✅ Done |
| 🟢 **CI Pipeline** | Lint → Test → Summary with fail-fast | ✅ Done |
| 🏗️ **Context Retrieval** | AST-based code context retrieval (next phase) | 🔧 Planned |

---

## 🏗️ System Architecture

```
PR URL
  │
  ▼
┌─────────────┐
│   github/    │   PR URL parsing + GitHub API v3 client
│  parser.py   │   (retry, rate-limit, error mapping)
│  client.py   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   review/    │   Unified diff parsing
│ diff_parser  │   File/Hunk/Line parsing
│    .py       │   Function/Class detection (Python/TS/Go/Java...)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    risk/     │   Risk detection engine (8 categories)
│  engine.py   │   Weighted scoring + safe path filtering
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│          backend/ (FastAPI)          │
│                                     │
│  ReviewService (compat facade)       │
│    └── WorkflowService (LangGraph)   │
│        ├── ParsePRNode               │
│        ├── FetchPRNode               │
│        ├── DiffAnalysisNode          │
│        ├── RiskDetectionNode         │
│        ├── ReviewGenerationNode      │
│        └── ReportGenerationNode      │
│                                     │
│  output: Structured JSON Report     │
└─────────────────────────────────────┘
```

### Data Flow

```
① POST /api/v1/review  { pr_url: "..." }
② github/parser  →  pr.owner, pr.repo, pr.number
③ github/client  →  PR metadata + unified diff
④ review/diff_parser  →  structured FileDiff, Hunk, ChangedLine
⑤ risk/engine  →  risk_level, score, matched_categories
⑥ WorkflowService  →  LangGraph state flow + LLM call + report_generator
⑦ Observability  →  review time, node latency, GitHub/LLM latency, tokens, risk score
⑧ Response 200  →  { summary, changed_modules, issues[], metrics }
```

---

## 🛠️ Technical Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI |
| **Workflow** | LangGraph state graph |
| **LLM** | DeepSeek V4 Pro / OpenAI GPT-4 / Qwen Max |
| **GitHub API** | requests (sync), httpx (async) |
| **Diff Parsing** | regex + AST (Python ast module) |
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS |
| **Database** | SQLite (MVP) → PostgreSQL (production) |
| **Testing** | pytest / unittest, root suite 177 tests + backend suite 89 tests |
| **CI/CD** | GitHub Actions (lint → test → summary) |
| **Code Quality** | ruff, flake8, mypy (strict) |
| **Container** | Docker + Docker Compose |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+ (for frontend)
- DeepSeek / OpenAI API key
- GitHub token (optional, for higher rate limits)

### 5-Minute Setup

```bash
# Clone
git clone https://github.com/soren-max/PR-AI-Reviewer.git
cd PR-AI-Reviewer

# Backend
cd ai-pr-review/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # Edit with your API keys

# Start backend
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# Frontend (new terminal)
cd ai-pr-review/frontend
cp .env.local.example .env.local
npm install && npm run dev
# → http://localhost:3000
```

### Docker

```bash
docker compose -f ai-pr-review/infra/docker-compose.yml up --build
```

---

## ⚙️ Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek API key |
| `LLM_PROVIDER` | ❌ | `deepseek` | `deepseek` / `openai` / `qwen` |
| `GITHUB_TOKEN` | ❌ | — | GitHub PAT (60 req/h without) |
| `DATABASE_URL` | ❌ | `sqlite+aiosqlite:///./data/reviews.db` | Database URL |
| `DEEPSEEK_MODEL` | ❌ | `deepseek-chat` | Model identifier |

---

## 📖 API Reference

### Submit PR for Review

```bash
curl -X POST http://localhost:8000/api/v1/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/42"}'
```

**Response** (200):

```json
{
  "pr_url": "https://github.com/owner/repo/pull/42",
  "owner": "owner",
  "repo": "repo",
  "pull_number": 42,
  "pr_title": "Fix login redirect",
  "report": "...",
  "input_tokens": 450,
  "output_tokens": 180,
  "model": "deepseek-chat",
  "metrics": {
    "review_time_ms": 2300,
    "workflow_latency_ms": 2300,
    "github_api_latency_ms": 420,
    "llm_latency_ms": 1700,
    "prompt_length_chars": 12840,
    "prompt_tokens": 450,
    "completion_tokens": 180,
    "total_tokens": 630,
    "risk_score": 85,
    "risk_level": "high",
    "node_latency_ms": {
      "parse_pr": 1,
      "fetch_pr": 420,
      "review_generation": 1700
    }
  }
}
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "version": "0.2.0"}
```

### Workflow Compatibility

The synchronous review API is unchanged. Internally, `ReviewService` now delegates to a LangGraph-backed `WorkflowService`:

```text
PR URL → Parse PR → Fetch PR → Diff Analysis → Risk Detection → Review Agent → Report Agent → Output
```

The Week2 prompt and response shape are preserved. See [docs/LANGGRAPH_WORKFLOW.md](docs/LANGGRAPH_WORKFLOW.md) for the workflow design and extension points.

---

## 🔧 Development Workflow

```text
Issue → Branch → Commit → PR → CI → Review → Merge → Runnable main
```

### Branch Naming

```
feat/<description>     # New feature
fix/<description>      # Bug fix
docs/<description>     # Documentation
refactor/<description> # Refactor
test/<description>     # Tests
```

### Commit Convention (Conventional Commits)

```
feat(review): add risk detection engine
feat(diff): add function detection in diff parser
fix(github): handle paginated API responses
test(parser): add edge cases for URL parsing
docs(readme): update project roadmap
refactor(service): extract prompt builder
ci: add coverage threshold to test workflow
```

### Local Verification

```bash
make test         # pytest tests/
make lint         # ruff + flake8 + mypy
make ci           # lint + test (same as CI)
```

## 📝 PR Standards

1. **All features must be developed via PRs** — no direct commits to `main`
2. **Each PR does ONE thing** — large features split into multiple small PRs
3. **PR template includes**: title, description, implementation approach, testing method, risk assessment
4. **CI must pass** before merge
5. **Main branch must stay runnable** at all times

See [`.github/pull_request_template.md`](.github/pull_request_template.md) and [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

---

## 🧪 Testing

```bash
# All tests
python -m pytest tests/ -v --cov

# Specific test file
python -m pytest tests/test_parser.py -v

# With coverage threshold
python -m pytest tests/ --cov-fail-under=80
```

**Current verification baseline**: root suite 177 tests with 85%+ coverage, plus backend suite 89 tests across API, workflow, metrics, GitHub, LLM, report, and task paths.

---

## 📅 Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for detailed milestones.

| Stage | Status |
|---|---|
| **Stage 0** — Repository Foundation | ✅ Complete |
| **Stage 1** — PR Fetch + Diff Engine | ✅ Complete |
| **Stage 2** — Review Engine + Pipeline | ✅ Complete |
| **Stage 3** — Agent Workflow + Observability | ✅ Complete |
| **Stage 4** — Context Retrieval V1 | 📅 Planned |
| **Stage 5** — Multi-Model Evaluation | 📅 Planned |
| **Stage 6** — GitHub Webhooks + Batch Review | 📅 Planned |

---

## 📊 Project Status

| Area | Status |
|---|---|
| Core pipeline (URL → fetch → diff → risk → review) | ✅ Production-ready |
| Backend API | ✅ `POST /api/v1/review` |
| Frontend | ✅ Next.js SPA |
| LLM providers | ✅ DeepSeek / OpenAI / Qwen |
| Observability | ✅ Review workflow metrics surfaced in API and frontend |
| Test coverage | ✅ Root suite 177 tests, backend suite 89 tests, ≥80% |
| CI/CD | ✅ GitHub Actions |
| Enterprise docs | ✅ PRD / Roadmap / Acceptance / Workflow |
| Context Retrieval | 📅 Stage 4 |

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built with ❤️ for engineering teams who want better code reviews</sub>
</p>
