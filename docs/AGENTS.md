# Agents

## Operating Model

This project uses a staged collaboration model:

```text
Reasonix: requirements analysis + task breakdown + initial development
Codex: code review + architecture hardening + tests + refactor
User: acceptance + git commit + merge
```

## Codex Responsibilities

- Read `docs/PROJECT_RULES.md` before substantial code changes.
- Preserve existing behavior unless the task explicitly changes it.
- Prefer minimal, well-tested improvements.
- Add tests for every changed behavior.
- Run focused verification and report results.
- Keep the project aligned with enterprise AI Code Review Platform goals.

## Review Responsibilities

When reviewing or hardening the project, Codex should check:

- Architecture boundaries
- Duplicate logic
- Prompt quality
- GitHub API correctness
- LLM provider abstraction
- Error handling
- Logging
- Security
- Performance
- Token usage
- Tests
- Deployment readiness

## Escalation

If a requested change would prematurely add roadmap complexity, Codex should explain the risk and recommend the smallest useful next step.

