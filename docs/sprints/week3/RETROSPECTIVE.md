# Sprint 3 Retrospective

## Completed

- Migrated the synchronous PR review pipeline to a LangGraph workflow.
- Added `ReviewState` with PR, diff, risk, review, report, error, latency, token, metrics, and checkpoint metadata.
- Split workflow orchestration into single-purpose nodes.
- Preserved the existing FastAPI API contract through `ReviewService`.
- Added conditional error recovery and retry for external GitHub and LLM calls.
- Reserved a checkpoint interface without adding persistence.
- Added review workflow observability for latency, token, prompt length, and risk metrics.
- Added frontend cards for Review Time, Prompt Tokens, Completion Tokens, and Risk Score.
- Added workflow, node, metrics, API, mocked GitHub, and mocked LLM tests.
- Updated README, ROADMAP, CHANGELOG, architecture docs, and LangGraph workflow docs.

## Not Completed

- No Tree-sitter implementation.
- No Code RAG.
- No Harness integration.
- No MCP integration.
- No Redis or PostgreSQL.
- No new specialist agents.
- No new API endpoints or pages.

These omissions are intentional Sprint 3 scope control, not missed deliverables.

## Technical Debt

| Item | Severity | Plan |
|---|---|---|
| Root prototype modules and `ai-pr-review/` product modules still coexist. | Medium | Keep adapters stable; consolidate only when a future stage needs it. |
| Prompt length metrics are measured by rebuilding the canonical prompt before provider invocation. | Low | In a later metrics refactor, let providers return prompt metadata directly. |
| Frontend dependency install is not locked by a committed lockfile. | Medium | Add a lockfile in a dedicated frontend dependency hygiene PR. |

## Architecture Debt

| Item | Severity | Plan |
|---|---|---|
| Background task review path still uses the older async task pipeline, while synchronous review uses LangGraph. | Medium | Decide in Sprint 4 or Sprint 5 whether background reviews should delegate to `WorkflowService`. |
| Checkpointing is interface-only. | Low | Keep it reserved until persistence is introduced in a production-readiness sprint. |
| Observability is returned in API payloads but not persisted. | Low | Persist metrics only after the storage layer is upgraded. |

## Bugs Found

| Priority | Bug | Resolution |
|---|---|---|
| P2 | Compatibility prompt builder diverged from the canonical LLM prompt builder. | Fixed by re-exporting the canonical builder and adding a regression test. |

## Lessons Learned

- LangGraph is valuable once workflow state, retries, conditional recovery, and future checkpointing matter.
- Keeping `ReviewService` as a facade made the migration low-risk for API and frontend consumers.
- Observability should be added before evaluation/harness work so later quality gates can reuse real metrics.
- Strict PR boundaries made the Sprint easier to review: workflow and observability stayed as separate PRs.

## Sprint Velocity

| Metric | Value |
|---|---|
| Completed PRs | 2 feature PRs + 1 final review PR |
| Merged feature PRs | #4, #6 |
| New major modules | `WorkflowService`, workflow nodes, `ReviewMetrics` |
| Backend test count | 89 |
| Root test count | 177 |
| Root coverage | 85%+ |
| CI status | Green |

## Sprint 4 Plan

Sprint 4 should begin with Context Retrieval V1, not a broad multi-language parser rollout.

Recommended order:

1. Add Python AST parser.
2. Build symbol table from changed files.
3. Build import graph.
4. Add shallow call graph for changed functions.
5. Format retrieved context for the existing review prompt.
6. Add tests for parser, graph builder, and prompt context bounds.

Tree-sitter for TypeScript/JavaScript should wait until the Python retrieval path is proven and covered.
