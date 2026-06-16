# Week2 Engineering Report

Date: 2026-06-16

## Goal

Week2 goal is to make the project genuinely capable of AI-assisted PR review, not only fetching a PR and displaying an LLM response.

Required scope:

- Diff Analysis
- Risk Detection
- Review Prompt V2
- JSON structured output
- pytest
- Mock Test
- GitHub Actions

Forbidden scope:

- LangGraph
- Tree-sitter
- RAG
- MCP
- Harness

## Completion

| Area | Completion |
| --- | ---: |
| 功能完成 | 90% |
| 工程质量 | 86% |
| 测试覆盖 | 84% |
| AI Review | 82% |
| 综合评分 | 86/100 |

## Completed Work

### Diff Analysis

Reason:
PR Review must understand file-level and line-level changes before asking the model to judge risk.

Impact:
Without deterministic diff analysis, the system can only summarize text and cannot reliably locate changed files, deleted files, or high-risk hunks.

Best Practice:
Keep lightweight deterministic diff parsing in the review domain, and pass normalized changes to later risk and model layers.

Implementation:
`ai-pr-review/backend/app/services/review/diff_parser.py` now contains backend-owned diff parsing logic, so the backend no longer depends on root prototype modules at runtime.

### Risk Detection

Reason:
High-risk files and change patterns should be detected before LLM analysis, then provided as model context.

Impact:
This improves recall for auth, security, database, config, payment, deletion, and dependency changes while reducing purely prompt-driven misses.

Best Practice:
Use deterministic risk signals as model input, not as a replacement for model reasoning.

Implementation:
`ai-pr-review/backend/app/services/review/risk_analyzer.py` produces risk context and `ReviewService` forwards that context into the LLM prompt.

### Review Prompt V2

Reason:
The previous prompt did not enforce a stable output contract strongly enough.

Impact:
Unstructured review output is hard to render, test, aggregate, or compare across model providers.

Best Practice:
Use a single canonical prompt contract with explicit severity, category, location, issue body, suggestion, and code snippet requirements.

Implementation:
`prompts/pr_review_agent.md` now requires JSON-only output and standard fields for PR summary, changed modules, issues, and score.

### JSON Structured Output

Reason:
The API and frontend need predictable review objects instead of free-form markdown.

Impact:
Stable JSON reduces UI breakage, enables future issue deduplication, and makes mock testing reliable.

Best Practice:
Parse and normalize model output defensively, while moving toward strict schema validation.

Implementation:
`report_generator.py` supports Review Prompt V2 fields and keeps legacy compatibility for older provider output.

### pytest and Mock Test

Reason:
PR review systems rely on external APIs and LLMs, so deterministic mock tests are mandatory.

Impact:
Without mock tests, CI is slow, flaky, expensive, and unsafe.

Best Practice:
Mock GitHub, LLM providers, and background review tasks at service/API boundaries.

Implementation:
Backend tests now cover API, services, GitHub behavior, LLM behavior, and task orchestration using mocks and FastAPI dependency overrides.

### GitHub Actions

Reason:
Week2 quality must be enforced automatically.

Impact:
Manual validation does not scale and allows regressions before Week3.

Best Practice:
CI should run lint, compile checks, and deterministic tests without real credentials.

Implementation:
`.github/workflows/ci.yml` now runs backend Ruff, compileall, pytest, and selected legacy tests with dummy API keys.

## Test Result

Backend:

```text
77 passed in 13.75s
```

Legacy selected tests:

```text
146 passed in 0.12s
```

Lint:

```text
All checks passed!
```

Compile:

```text
python3 -m compileall app
```

Result:
passed.

## Week3 Readiness

Decision:
The project reaches the Week3 entry bar.

Constraints:

- Enter Week3 only after user acceptance and commit.
- Week3 should not jump directly to LangGraph or full RAG.
- Week3 should first define code context retrieval boundaries, schema, caching strategy, and evaluation examples.

## Remaining Risks

### P0

None.

### P1

Legacy root tests and prototype modules are still present.

Impact:
They create confusion and require selective CI execution.

Fix:
Migrate useful tests into backend and archive or remove obsolete prototype modules.

### P1

LLM JSON output is normalized but not yet enforced by a strict Pydantic Review JSON schema.

Impact:
Provider drift may still cause inconsistent downstream behavior.

Fix:
Introduce a canonical `ReviewOutput` schema and validate every model response before report generation.

### P2

Frontend lacks automated tests.

Impact:
API response changes can break rendering without CI detection.

Fix:
Add frontend component tests and API contract smoke tests.

## Enterprise Standard Judgment

Current status:
The project is no longer a simple demo. It now has the minimum engineering foundation expected from an AI PR Review MVP: PR/Diff ingestion, risk analysis, structured model output, mock tests, and CI.

Final judgment:
It has reached the standard to enter Week3, but it has not yet reached the complete standard of a medium-to-large internet company AI application. The next engineering milestone must focus on context quality, schema enforcement, observability, and removal of legacy duplication.
