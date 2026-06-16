## Title

<!-- Use Conventional Commits, for example: feat(review): add risk detection engine -->

## Summary

<!-- What does this PR change? Keep it focused on one thing. -->

Closes #

## Implementation Approach

<!-- Explain the design and important trade-offs. -->

## Test Plan

<!-- List commands and results. -->

- [ ] Backend Ruff: `cd ai-pr-review/backend && python -m ruff check app tests`
- [ ] Backend compile: `cd ai-pr-review/backend && python -m compileall app`
- [ ] Backend pytest: `cd ai-pr-review/backend && python -m pytest -q`
- [ ] Legacy selected tests:

```bash
python3 -m pytest \
  tests/test_parser.py \
  tests/test_github_client.py \
  tests/test_diff_analyzer.py \
  tests/test_risk_engine.py \
  -q
```

- [ ] Frontend typecheck/lint if frontend changed:

```bash
cd ai-pr-review/frontend
npm run typecheck
npm run lint
```

## Risk Impact

<!-- Runtime, API compatibility, security, performance, token cost, data migration, or deployment risk. -->

## Screenshots or Demo

<!-- Required for frontend changes. Use "Not applicable" for backend/docs-only changes. -->

## Checklist

- [ ] This PR does exactly one thing.
- [ ] This PR is small enough to review and merge within 1-2 days.
- [ ] I did not commit directly to `main`.
- [ ] I added or updated tests when behavior changed.
- [ ] I updated docs when workflow, API, architecture, or behavior changed.
- [ ] I did not commit secrets, `.env`, local databases, caches, or generated build output.
- [ ] Main branch will remain runnable after merge.
