# Product Requirements Document (PRD)

## Product Name

**AI PR Review Platform**

## Mission

Build an enterprise-grade AI Code Review Platform that helps engineering teams review GitHub Pull Requests faster and with higher quality.

The platform is not intended to replace human reviewers. It provides a reliable AI-assisted first pass that summarizes changes, detects risk, and generates actionable review suggestions before maintainers spend focused review time.

## Target Users

- **Backend engineers** reviewing service and API changes
- **Frontend engineers** reviewing UI and API contract changes
- **Tech leads** reviewing architecture, risk, and maintainability
- **QA engineers** validating regression risk
- **Engineering managers** needing review quality and delivery visibility

## User Journey

```text
1. Developer opens a GitHub PR
2. Developer pastes PR URL into AI PR Review
3. System fetches PR metadata and diff
4. System analyzes diff structure and detects risk signals
5. System builds a structured prompt and calls LLM
6. System generates a structured review report
7. Developer reads the report before human review
8. Human reviewer uses the AI report as baseline
```

## Core Requirements

### R1: GitHub PR Input
- Accept any public GitHub PR URL
- Parse owner, repo, pull_number
- Validate URL format

### R2: PR Data Retrieval
- Fetch PR metadata (title, description, author, branches)
- Fetch changed files with patches
- Handle rate limiting and retry

### R3: Diff Analysis
- Parse unified diff format
- Extract file paths, changed lines
- Detect modified functions and classes
- Support Python, TypeScript, Go, Java

### R4: Risk Detection
- Identify high-risk modules (auth, payment, security, database)
- Weight-based scoring system
- Safe path filtering (docs, tests, assets)

### R5: AI Review Generation
- Structured system prompt for LLM
- JSON output format for machine parsing
- Bug / Security / Performance / Maintainability dimensions
- False positive control rules

### R6: Review Report
- Summary of PR changes
- Severity-categorized issues
- File and line references
- Actionable fix suggestions

### R7: API + Frontend
- FastAPI synchronous review endpoint
- Next.js frontend with Markdown rendering
- Error handling for all failure modes

## Non-Functional Requirements

| Area | Requirement |
|---|---|
| **Accuracy** | Prompt includes false-positive control rules |
| **Speed** | Single-request response < 120s |
| **Testability** | ≥80% code coverage, all external APIs mocked |
| **Maintainability** | Clean Architecture: Domain / Service / Infrastructure |
| **Extensibility** | Multi-LLM support via abstract base class |
| **Security** | API keys via environment variables, no secrets in code |

## Success Metrics

| Metric | Target |
|---|---|
| Test pass rate | 100% |
| Code coverage | ≥80% |
| CI pipeline | All jobs green |
| Eval recall (Golden Dataset) | ≥85% |
| False positive rate | <15% |
