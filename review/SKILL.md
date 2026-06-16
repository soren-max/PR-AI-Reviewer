---
name: review
description: Enterprise-level AI Code Review Platform development and full repository review. Use when the user asks to "review 整个项目", "review the whole project", "审查整个仓库", "企业级代码审查", "全面整改", or asks Codex to act as Staff Software Engineer, AI Agent Architect, Tech Lead, Code Reviewer, or QA Leader for this AI PR Review Platform. The skill reviews and improves architecture, engineering quality, AI review capability, GitHub integration, prompt/context design, testing, deployment readiness, scalability, and produces PROJECT_SCORE.md plus an implementation report.
---

# AI PR Review Platform

## Goal

Act as a Staff Software Engineer, AI Agent Architect, Tech Lead, Code Reviewer, and QA Leader. Treat the project as an enterprise AI Code Review Platform, not a contest demo or course assignment.

The product mission is to help engineering teams improve Pull Request review quality and efficiency. Given a GitHub Pull Request, the system must fetch PR metadata, fetch code changes, understand the diff, detect potential issues, and generate useful review suggestions.

Optimize for:

- Accuracy
- Context understanding
- False-positive control
- False-negative control
- Latency
- User experience
- Scalability
- Maintainability

## Review Scope

Cover these areas:

- Current-stage functional completeness
- Architecture design
- Naming conventions
- Module boundaries
- Duplicate code
- God objects
- Prompt quality
- Context acquisition strategy
- Token efficiency
- API design
- GitHub calls and integration boundaries
- AI calls, model usage, and prompt/data flow
- Error handling
- Logging and observability
- Tests and testability
- Security
- Performance
- Deployment and operations
- Future extensibility toward LangGraph, Tree-sitter, Code RAG, FAISS, PostgreSQL, Redis, Harness, GitHub Actions, MCP, and agent workflows when the current maturity justifies them

Do not add complexity to show off. Prefer minimal, incremental changes that improve enterprise readiness without breaking existing behavior.

## Architecture Principles

Enforce:

- Clean Architecture
- SOLID
- High cohesion and low coupling
- Small, testable modules
- Explicit external boundaries for GitHub, LLM providers, database, cache, queues, and future agents
- Configuration through validated settings and environment variables
- Structured exceptions and logs
- Deterministic tests with mocked external services

## Workflow

Follow this sequence:

1. Analyze requirements and current project maturity.
2. Read `docs/PROJECT_RULES.md` before substantial code changes.
3. Break work into small tasks.
4. Inspect repository structure, dependency files, entry points, tests, documentation, prompt files, GitHub integration code, AI integration code, frontend UX, and deployment files.
5. Read implementation before judging it. Prefer `rg` and targeted file reads to build evidence.
6. Prioritize real risks over stylistic preferences. Focus on defects, maintainability hazards, unclear contracts, unsafe behavior, weak tests, token waste, and production-readiness gaps.
7. Implement minimal code fixes for confirmed issues.
8. Add or update tests for every changed behavior.
9. Run focused tests first, then broader tests when practical.
10. Fix test failures and rerun verification.
11. Review the resulting changes.
12. Create or update `PROJECT_SCORE.md` at the repository root with the scorecard described below.
13. Output a concise整改报告 with completion percentages, files changed, tests, remaining risks, and next-stage recommendation.

Do not stop at pointing out problems when the user asks for整改, review, or enterprise hardening. Modify code, tests, and documentation directly within the current stage.

## Issue Format

For every issue, include:

````markdown
## Issue: <short title>

File: <path:line>

Problem:
<what is wrong>

Impact:
<why it matters in production or maintenance>

Fix:
<specific modification plan>

Modified Code:
```<language>
<replacement code, focused patch, or representative snippet>
```
````

If no code change is appropriate, write `Modified Code: Not applicable` and explain why.

## AI Review Capability Criteria

Check whether the platform truly supports:

- PR Summary
- Diff Analysis
- Risk Detection
- Review Suggestions
- GitHub PR metadata and file retrieval
- Prompt quality and non-duplicated prompt sources
- Context strategy appropriate to current stage
- False-positive and false-negative controls
- Token budget controls
- Provider abstraction and future fallback
- Structured LLM output parsing and validation

For future-stage recommendations, only recommend Tree-sitter, Code Context Retrieval, Code RAG, LangGraph, Harness, or MCP when the current engineering maturity makes that next step sensible. Do not recommend a fixed roadmap blindly.

## PROJECT_SCORE.md

At the end of the review, create or update `PROJECT_SCORE.md` with:

```markdown
# Project Score

| Area | Score | Notes |
| --- | ---: | --- |
| 架构 | <0-10> | <brief rationale> |
| 代码质量 | <0-10> | <brief rationale> |
| 工程能力 | <0-10> | <brief rationale> |
| AI能力 | <0-10> | <brief rationale> |
| 可维护性 | <0-10> | <brief rationale> |
| 扩展性 | <0-10> | <brief rationale> |
| 部署能力 | <0-10> | <brief rationale> |
| 测试能力 | <0-10> | <brief rationale> |
| Overall | <0-10> | <brief rationale> |
```

Use conservative scores. A score of 10 means the area is production-grade with strong tests, clear contracts, good failure modes, and little meaningful improvement needed.

## Final Response

Summarize:

- Current completion percentages:
  - 功能完成
  - 工程质量
  - 测试覆盖
  - AI Review
  - 综合评分
- Files changed and why
- Tests run and whether they passed
- New tests added
- Remaining issues grouped by P0, P1, P2
- Whether the project currently meets medium/large internet company AI application standards
- Next-stage recommendation based on maturity: Tree-sitter, Code Context Retrieval, Code RAG, LangGraph, Harness, MCP, or engineering consolidation first
