# Contributing to AI PR Review

Thank you for considering contributing! This document provides guidelines to keep the codebase maintainable and reviews productive.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Commit Message Convention](#commit-message-convention)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

All contributors must adhere to our [Code of Conduct](./CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository and clone your fork.
2. Read the [README](./README.md) for project overview.
3. Set up the development environment as described below.
4. Find an issue to work on — look for labels `good first issue` or `help wanted`.

## Development Setup

### Prerequisites

- **Python** 3.11+
- **pip** (latest)

### Step-by-step

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/ai-pr-review.git
cd ai-pr-review

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate     # Linux/macOS
# .venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Copy environment variables
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (required)

# 5. Verify setup
make test
make lint
```

## Coding Standards

### Python

- **Style**: [PEP 8](https://peps.python.org/pep-0008/), enforced by **ruff** and **flake8**
- **Type annotations**: Required for all functions (checked by **mypy** in `--strict` mode)
- **Formatting**: **ruff formatter** (line length 88)
- **Imports**: sorted via **ruff** (isort-compatible grouping):
  1. Standard library
  2. Third-party
  3. First-party (`app.*`)
  4. Type-only
- **Naming**:
  - `snake_case` for functions, methods, variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Docstrings

Use **Google-style** docstrings for all public APIs:

```python
def analyze_pr(diff: str, model: str = "gpt-4") -> ReviewResult:
    """Run AI analysis on a PR diff.

    Args:
        diff: Unified diff string of the PR.
        model: OpenAI model identifier.

    Returns:
        ReviewResult containing issues and score.

    Raises:
        AIClientError: If the API call fails or returns invalid output.
    """
```

### File Organization

| File | Responsibility |
|------|---------------|
| `app/main.py` | Application entry point, CLI or server |
| `app/github_client.py` | GitHub API client (PR metadata, diff fetching) |
| `app/ai_reviewer.py` | LLM interaction, prompt construction, response parsing |
| `tests/` | pytest test suite, mirroring `app/` structure |

## Testing

- **Framework**: pytest with pytest-asyncio
- **Coverage target**: ≥ 85% (enforced in CI)
- **Test location**: `tests/`, mirror the `app/` module structure
- **External calls**: Always mock GitHub API and OpenAI API in unit tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run a specific test file
python -m pytest tests/test_ai_reviewer.py -v

# Run tests matching a keyword
python -m pytest -k "parse_prompt"
```

### Test Structure

```python
# tests/test_ai_reviewer.py
class TestBuildPrompt:
    def test_includes_diff_content(self):
        ...

class TestParseResponse:
    def test_valid_json(self):
        ...

    def test_malformed_json_raises(self):
        ...
```

## Pull Request Process

1. **Create a feature branch** from `main`:

   ```bash
   git checkout -b feat/my-feature-name
   ```

2. **Make your changes**, keeping commits focused and atomic.
3. **Run all checks locally**:

   ```bash
   make ci       # lint → typecheck → test
   ```

4. **Push and open a PR** against `main`.
5. **Fill out the PR template** completely.
6. **Respond to reviewer feedback** with commits (no force-push during review unless necessary).
7. **A maintainer will merge** once all checks pass and at least one approval is received.

### PR Title Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

Examples:
  feat(analyzer): add support for multi-file chunking
  fix(github): handle paginated file responses
  docs: add architecture decision record for SQLite
  refactor(ai): extract prompt builder into separate module
```

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`.

## Reporting Issues

See the [issue templates](.github/ISSUE_TEMPLATE/) for bug reports and feature requests. A good issue includes:

- Clear, minimal reproduction steps
- Expected vs. actual behavior
- Environment details (OS, Python version, package version)

---

*Thank you for helping improve AI PR Review!*
