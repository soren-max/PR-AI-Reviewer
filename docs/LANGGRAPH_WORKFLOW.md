# LangGraph Review Workflow

## Purpose

Sprint 3 moves the synchronous PR review pipeline from a linear service method to a LangGraph state workflow while preserving the existing API contract.

The public flow remains:

```text
GitHub PR URL → Review JSON/Markdown output
```

Internally, the workflow is now:

```text
PR URL
→ Parse PR
→ Fetch PR
→ Diff Analysis
→ Risk Detection
→ Review Agent
→ Report Agent
→ Output
```

## Why Not a Plain Pipeline

A plain async pipeline is enough for Week2 behavior, but it becomes brittle once review logic becomes agentic. The next stages need branches, retries, recoverable failures, optional checkpoints, and later multi-agent coordination.

LangGraph gives the project:

- Explicit `ReviewState` passed between nodes.
- Single-responsibility nodes that can be tested independently.
- Conditional edges for error recovery.
- Retry boundaries around external GitHub and LLM calls.
- A clear place to add checkpoint persistence later.
- A graph shape that can grow into multi-agent workflows without changing the API surface.

## State

`ReviewState` is defined in `ai-pr-review/backend/app/services/review/state.py` and includes:

- `pr_url`
- `owner`
- `repo`
- `pull_number`
- `pr_info`
- `changed_files`
- `diff_analysis`
- `risk_analysis`
- `review_result`
- `final_report`
- `errors`
- `latency`
- `token_usage`

The state also carries `language`, `diff_text`, `last_exception`, and a reserved `checkpoint` handle used by future persistence work.

## Nodes

| Node | Responsibility |
|---|---|
| `ParsePRNode` | Parse and validate the GitHub PR URL |
| `FetchPRNode` | Fetch PR metadata and changed files from GitHub |
| `DiffAnalysisNode` | Parse unified diff text into the domain diff model |
| `RiskDetectionNode` | Run deterministic risk analysis from changed paths |
| `ReviewGenerationNode` | Call the existing Week2 review agent prompt through the configured LLM |
| `ReportGenerationNode` | Convert LLM output into the existing final report model |
| `ErrorRecoveryNode` | End failed workflows with errors preserved in state |

Each node owns one concern. External calls are mocked in tests.

## Error Recovery and Retry

After each node, the graph uses a conditional edge:

```text
errors? yes → ErrorRecoveryNode → END
errors? no  → next node
```

`FetchPRNode` and `ReviewGenerationNode` retry transient failures. Domain errors such as invalid PR URLs and missing PRs are recorded and preserved so the API layer can keep returning the existing 422, 404, or 502 responses.

## Checkpointing

`ReviewCheckpoint` is defined as an interface only. Sprint 3 does not add persistence, PostgreSQL, Redis, or LangGraph checkpoint storage. Future work can implement the protocol and inject it into `WorkflowService`.

## Compatibility

`ReviewService` remains the facade used by FastAPI. It delegates to `WorkflowService` and maps the final `ReviewState` back to `ReviewOutput`.

No API, frontend, input payload, output payload, review JSON schema, or Week2 prompt redesign is included in this change.

## Future Multi-Agent Extension

The current graph can grow by adding conditional branches after risk detection, for example:

- Security agent for high-risk auth, crypto, or permission changes.
- Performance agent for database, caching, or async hot paths.
- Maintainability agent for broad refactors.
- Report aggregation agent that merges specialist findings into one review result.

Those extensions should remain separate PRs. Tree-sitter, Code RAG, Harness, MCP, PostgreSQL, and Redis are intentionally out of scope for Sprint 3.
