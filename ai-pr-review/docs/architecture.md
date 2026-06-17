# AI PR Review — Architecture Document

## System Overview

```
┌────────────────────┐     ┌───────────────────────┐     ┌──────────────────┐
│   Next.js SPA      │────▶│   FastAPI Backend       │────▶│   DeepSeek V4 Pro│
│   (Port 3000)      │     │   (Port 8000)           │     │   API            │
└────────────────────┘     └───────────┬───────────┘     └──────────────────┘
                                        │
                              ┌─────────▼─────────┐
                              │ LangGraph Workflow │
                              │ ReviewState + Nodes│
                              └─────────┬─────────┘
                                        │
                              ┌────────▼────────┐
                              │   GitHub API     │
                              │   (External)     │
                              └─────────────────┘
```

Separate parser boundary:

```
Source Code
  │
  ▼
┌──────────────────────┐
│ ParserFactory         │  Python enabled
│ TreeSitterService     │  Java/Go/TypeScript reserved
└──────────┬───────────┘
           ▼
  Serializable AST
```

## Data Flow

```
1. User submits PR URL
2. Backend parses URL → creates Review (status=pending) → returns 201
3. Background task:
   a. status → fetching
   b. Fetch PR metadata + diff from GitHub API
   c. status → analyzing
   d. Build prompt → call DeepSeek API
   e. Parse LLM response → generate structured report
   f. Save report to DB → status → completed
4. Frontend polls status every 3s
5. status=completed → render report

For the synchronous `POST /api/v1/review` path:

```
PR URL
→ ParsePRNode
→ FetchPRNode
→ DiffAnalysisNode
→ RiskDetectionNode
→ ReviewGenerationNode
→ ReportGenerationNode
→ ReviewMetrics
→ existing ReviewResponse
```

`ReviewService` remains the compatibility facade used by the API layer. It delegates orchestration to `WorkflowService`, which compiles the LangGraph state graph and maps `ReviewState` back to the existing response model.

The synchronous response includes an additive `metrics` object with review time, workflow latency, GitHub API latency, LLM latency, prompt length, token usage, risk score, and per-node latency. These values are collected inside workflow state so future Harness and evaluation jobs can reuse the same observability payload without calling frontend-specific code.

On failure at any step:
   status → failed, error_code + error_detail set
```

## Key Design Decisions

- **BackgroundTasks**: MVP uses FastAPI's built-in `BackgroundTasks` instead of Celery/Redis to avoid infrastructure complexity. For production, migrate to Celery + Redis.
- **SQLite**: See [ADR-001](./adr/001-use-sqlite-for-mvp.md)
- **Single API call to LLM**: All files sent in one prompt. For large PRs (>20 files), truncate to top 15 most-changed files.
- **Polling not WebSocket**: MVP simplicity. Future: SSE or WebSocket for real-time updates.
- **LangGraph for review orchestration**: The synchronous review pipeline now uses explicit state and single-purpose nodes so future multi-agent review, checkpointing, and conditional branches can be added without changing the API contract.
- **Tree-sitter parser boundary**: `ParserFactory` and `TreeSitterService` provide standalone AST parsing. Sprint4 PR1 enables Python only and reserves Java, Go, and TypeScript extension points without changing the review workflow.

## Directory Responsibilities

### Backend

| Directory | Responsibility |
|-----------|---------------|
| `app/api/` | HTTP layer: route definitions, request validation, response serialization |
| `app/core/` | Cross-cutting concerns: configuration, database engine, exception hierarchy, logging |
| `app/models/` | SQLAlchemy ORM models: table definitions, relationships, query helpers |
| `app/schemas/` | Pydantic schemas: API request validation, response serialization, OpenAPI generation |
| `app/services/` | Business logic: GitHub client, LLM client, LangGraph workflow, prompt builder, report parser, Tree-sitter parser service |
| `app/tasks/` | Async workflow orchestration: the `run_review` pipeline |
| `tests/` | pytest test suite, mirrors app structure |

### Frontend

| Directory | Responsibility |
|-----------|---------------|
| `src/app/` | Next.js App Router: page components and layouts |
| `src/components/` | Reusable React components: forms, status display, report rendering |
| `src/lib/` | API client, utility functions, constants |
| `src/types/` | TypeScript type definitions (aligned with backend Pydantic schemas) |
