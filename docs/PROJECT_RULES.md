# Project Rules

This document is the stable engineering contract for the AI PR Review Platform. Every implementation, refactor, review, and test update should follow these rules unless a task explicitly changes the project standard.

## Product Direction

The project is an enterprise AI Code Review Platform, not a demo. Optimize for real engineering team workflows:

- Pull Request summary
- Diff analysis
- Risk detection
- Review suggestions
- Low false positives
- Low false negatives
- Fast enough feedback
- Clear user experience
- Extensible architecture

Do not add future-stage modules just because they are on the roadmap. Introduce LangGraph, Tree-sitter, Code RAG, FAISS, PostgreSQL, Redis, Harness, GitHub Actions, or MCP only when the current milestone requires them.

## Coding Standards

- Prefer simple, explicit code over clever abstractions.
- Keep changes minimal and localized.
- Use type annotations on public functions, service boundaries, schemas, and provider interfaces.
- Avoid hidden global state except validated application settings.
- Do not duplicate business logic across API, service, task, and frontend layers.
- Do not swallow exceptions silently.
- Do not log secrets, tokens, raw authorization headers, or full LLM prompts that may contain proprietary code.
- Keep comments short and useful. Explain why, not obvious what.

## Naming Standards

- Python modules and functions: `snake_case`.
- Python classes and Pydantic/SQLAlchemy models: `PascalCase`.
- Constants and environment variables: `UPPER_SNAKE_CASE`.
- TypeScript files and React components: component files use `PascalCase.tsx`; utilities use `camelCase.ts`.
- API paths use plural resources, for example `/api/v1/reviews`.
- Database fields should be explicit and stable; avoid vague names like `data`, `obj`, `payload` unless the schema is intentionally generic.

## FastAPI Directory Standards

Backend code under `ai-pr-review/backend/app` should follow this structure:

```text
app/
├── api/          # FastAPI routes and dependencies only
├── core/         # config, database, logging, exceptions
├── models/       # SQLAlchemy persistence models
├── schemas/      # Pydantic request/response schemas
├── services/     # business logic and external integrations
├── tasks/        # background task orchestration
└── main.py       # application assembly
```

Rules:

- API routes must not contain business logic beyond validation, dependency wiring, and response mapping.
- Services own orchestration and domain decisions.
- External calls must be behind service/provider interfaces.
- Database models must not call GitHub or LLM APIs.
- Background tasks must reuse services instead of duplicating orchestration logic.
- New provider integrations belong under `app/services/llm/` or another explicit provider package.

## Testing Standards

Every behavior change needs tests.

Required test types by change:

- Pure functions: unit tests.
- GitHub API code: mocked HTTP/client tests.
- LLM provider code: mocked provider/client tests.
- API routes: API tests with dependency overrides.
- Background tasks: integration-style tests with mocked external services and test database.
- Prompt changes: tests that assert required context is included and large inputs are bounded.
- Bug fixes: regression tests that fail before the fix.

Testing rules:

- Never call real GitHub or real LLM APIs in tests.
- Mock external services at the service/provider boundary.
- Keep tests deterministic and fast.
- Prefer focused tests first, then broader tests.
- If a full suite cannot run, document exactly what passed and what blocked the rest.

## Git Commit Standards

Use Conventional Commits:

```text
feat: add review queue status endpoint
fix: paginate GitHub PR file fetching
refactor: isolate review orchestration service
test: cover prompt truncation
docs: add project rules
chore: update tooling
```

Commit rules:

- One commit should represent one coherent change.
- Do not mix unrelated refactors with feature work.
- Include tests with code changes.
- Do not commit secrets, local databases, generated caches, or `.env` files.

## Git and Pull Request Standards

- All feature, fix, refactor, test, and CI changes must be developed through Pull Requests.
- Do not commit business code directly to `main`.
- Every PR must do exactly one thing.
- Large features must be split into multiple small PRs.
- Each PR should be small enough to complete in 1-2 working days.
- Every PR must include title, description, implementation approach, test method, risk impact, and screenshots or demo notes for frontend changes.
- PRs must pass required tests before merge.
- After every merge, `main` must remain runnable.

Recommended branch names:

```text
feature/diff-analysis
feature/risk-detection
feature/review-json-output
test/review-service
ci/github-actions
docs/development-workflow
```

## API Response Format

Successful responses should be typed with Pydantic schemas.

List responses should use:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "per_page": 20
}
```

Error responses should use:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  },
  "request_id": "uuid-or-null"
}
```

Rules:

- Use stable machine-readable `code` values.
- Include `request_id` when available.
- Do not expose stack traces to clients.
- Do not expose upstream secrets or raw provider responses that may contain sensitive data.

## Review JSON Schema

LLM review output should normalize into this internal shape:

```json
{
  "overall_score": 85,
  "summary": {
    "total_issues": 2,
    "critical_count": 0,
    "major_count": 1,
    "minor_count": 1,
    "info_count": 0
  },
  "issues": [
    {
      "file_path": "src/auth.py",
      "line_start": 42,
      "line_end": 45,
      "severity": "critical|major|minor|info",
      "category": "security|performance|bug|design|style|best_practice|readability",
      "title": "Short issue title",
      "body": "Why this is a problem",
      "suggestion": "Actionable fix",
      "code_snippet": "Optional focused snippet"
    }
  ]
}
```

Rules:

- Validate severity and category.
- Deduplicate repeated issues by file, line, and title.
- Cap the number of persisted comments.
- Preserve raw LLM output for debugging, but never rely on raw markdown as the canonical API contract.
- Prefer actionable issues over generic style comments.

## AI Review Quality Rules

- Include PR title, PR body, changed files, bounded diff content, and deterministic risk context in prompts.
- Truncate or chunk large diffs explicitly; never silently drop context.
- Bias against speculative findings.
- Prioritize changed lines and nearby context.
- Use static risk signals to guide attention, not as final judgment.
- Track input and output token usage.
- Keep provider-specific logic behind provider classes.

## Development Workflow

Use this loop for each task:

1. Requirement analysis.
2. Task breakdown.
3. Code implementation.
4. Code review.
5. Add or update tests.
6. Run tests.
7. Fix failures.
8. Rerun verification.
9. Output remediation report.

Recommended collaboration rhythm:

```text
Reasonix: requirements analysis + task breakdown + initial development
Codex: code review + architecture hardening + tests + refactor
User: acceptance + git commit + merge
Next iteration
```
