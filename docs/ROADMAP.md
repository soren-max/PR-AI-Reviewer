# Roadmap

This roadmap defines the project scope and milestone sequence.
Each stage must be complete before the next begins.

---

## Stage 0: Repository Foundation ✅

**Goal**: Make the repository work like a real engineering team project.

| Deliverable | Status |
|---|---|
| Enterprise README with architecture and quick start | ✅ Complete |
| CONTRIBUTING guide with PR/commit standards | ✅ Complete |
| PR template | ✅ Complete |
| Issue templates (bug + feature) | ✅ Complete |
| Development workflow documentation | ✅ Complete |
| CI workflow (lint → test → summary) | ✅ Complete |
| Conventional Commits enforcement | ✅ Complete |

---

## Stage 1: PR Fetch + Diff Engine ✅

**Goal**: Reliably fetch and parse GitHub PR data.

| Deliverable | Status |
|---|---|
| PR URL parser (github/parser.py) | ✅ Complete |
| GitHub API v3 client (github/client.py) | ✅ Complete |
| Retry + rate-limit handling | ✅ Complete |
| Unified diff parser (review/diff_parser.py) | ✅ Complete |
| Function/Class detection (7 languages) | ✅ Complete |
| Unit tests (130+) | ✅ Complete |

---

## Stage 2: Review Engine + Pipeline ✅

**Goal**: End-to-end review from PR URL to structured report.

| Deliverable | Status |
|---|---|
| Risk detection engine (risk/engine.py) | ✅ Complete |
| 8 risk categories with weighted scoring | ✅ Complete |
| Enterprise review prompt (JSON output) | ✅ Complete |
| Report generator (Markdown + JSON) | ✅ Complete |
| FastAPI endpoint (`POST /api/v1/review`) | ✅ Complete |
| Next.js frontend | ✅ Complete |
| Multi-LLM support (DeepSeek/OpenAI/Qwen) | ✅ Complete |

---

## Stage 3: Agent Workflow ✅

**Goal**: Run the PR review pipeline through a stateful LangGraph workflow.

| Deliverable | Status |
|---|---|
| `ReviewState` with PR, diff, risk, review, report, error, latency, and token metadata | ✅ Complete |
| LangGraph workflow service | ✅ Complete |
| Parse PR, Fetch PR, Diff Analysis, Risk Detection, Review Generation, Report Generation nodes | ✅ Complete |
| State flow with conditional error recovery | ✅ Complete |
| Retry for external GitHub and LLM calls | ✅ Complete |
| Checkpoint extension interface reserved for future persistence | ✅ Complete |
| Backwards-compatible `ReviewService` facade | ✅ Complete |
| Workflow unit, node, integration, API compatibility, and mocked external API tests | ✅ Complete |
| Review workflow observability metrics in API and frontend | ✅ Complete |
| Sprint Review and Retrospective documentation | ✅ Complete |

---

## Stage 4: Context Retrieval V1 📅

**Goal**: Enrich review with code context beyond the diff.

| Deliverable | Status |
|---|---|
| Python AST parser (Tree-sitter foundation only) | ✅ Complete |
| Symbol table builder (Code Symbol Index foundation) | ✅ Complete |
| Call graph construction | 📅 Planned |
| Import graph construction | 📅 Planned |
| Context formatter → Prompt integration | 📅 Planned |
| TypeScript/JS tree-sitter parser | 📅 Planned |

---

## Stage 5: Multi-Model Evaluation 📅

**Goal**: Benchmark and compare LLM performance.

| Deliverable | Status |
|---|---|
| Golden Dataset (30 cases × 3 categories) | ✅ Complete |
| Eval runner (automated scoring) | ✅ Complete |
| Multi-model batch runner | 📅 Planned |
| Automated regression testing in CI | 📅 Planned |
| Model switch recommendation engine | 📅 Planned |

---

## Stage 6: GitHub Integration 📅

**Goal**: Integrate directly with GitHub workflow.

| Deliverable | Status |
|---|---|
| GitHub Webhook receiver | 📅 Planned |
| OAuth App authentication | 📅 Planned |
| Automated PR comment posting | 📅 Planned |
| Inline review suggestions via GitHub API | 📅 Planned |
| Batch review for repository | 📅 Planned |

---

## Stage 7: Production Readiness 📅

**Goal**: Deployable, monitored, production-grade.

| Deliverable | Status |
|---|---|
| PostgreSQL migration | 📅 Planned |
| Redis caching layer | 📅 Planned |
| Celery async task queue | 📅 Planned |
| Prometheus + Grafana monitoring | 📅 Planned |
| Load testing (Locust) | 📅 Planned |
| SLA targets (p95 < 60s) | 📅 Planned |
