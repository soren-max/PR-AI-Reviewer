# =============================================================================
# AI PR Review — Makefile
# =============================================================================
# Usage: make <target>
# =============================================================================

.DEFAULT_GOAL := help

.PHONY: help install run test test-cov lint format typecheck ci \
        clean docker-build docker-up docker-down \
        migrate migrate-up migration

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
PYTHON     := python3
PIP        := $(PYTHON) -m pip
PYTEST     := $(PYTHON) -m pytest
RUFF       := $(PYTHON) -m ruff
FLAKE8     := $(PYTHON) -m flake8
MYPY       := $(PYTHON) -m mypy
UVICORN    := $(PYTHON) -m uvicorn
ALEMBIC    := $(PYTHON) -m alembic

APP_MODULE := app.main:app
HOST       := 0.0.0.0
PORT       := 8000

# Detect OS for sed in-place flag
UNAME_S    := $(shell uname -s)
SED_INPLACE := $(if $(filter Darwin,$(UNAME_S)),-i '',-i)

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
install: .venv/bin/activate  ## Install all dependencies (.venv)

.venv/bin/activate: requirements.txt requirements-dev.txt
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt
	touch .venv/bin/activate

install-prod: ## Install only production dependencies
	$(PIP) install -r requirements.txt

# ---------------------------------------------------------------------------
# Development server
# ---------------------------------------------------------------------------
run: ## Start the FastAPI development server (with hot-reload)
	$(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

run-prod: ## Start the FastAPI production server
	$(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) --workers 4

# ---------------------------------------------------------------------------
# Linting & formatting
# ---------------------------------------------------------------------------
lint: lint-ruff lint-flake8 lint-mypy ## Run all linters

lint-ruff: ## Run ruff linter
	$(RUFF) check app/ tests/

lint-flake8: ## Run flake8 linter
	$(FLAKE8) app/ tests/ --count --statistics

lint-mypy: ## Run mypy type checker
	$(MYPY) app/ --strict --ignore-missing-imports

format: ## Format code with ruff
	$(RUFF) format app/ tests/

format-check: ## Check formatting without modifying files
	$(RUFF) format app/ tests/ --check --diff

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test: ## Run all tests with verbrose output
	$(PYTEST) tests/ -v --tb=short

test-cov: ## Run all tests with coverage report
	$(PYTEST) tests/ \
		-v \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=85

test-file: ## Run tests in a specific file: make test-file f=tests/test_ai_reviewer.py
	$(PYTEST) $(f) -v

test-match: ## Run tests matching keyword: make test-match k=parse_prompt
	$(PYTEST) tests/ -v -k "$(k)"

# ---------------------------------------------------------------------------
# CI (full pipeline)
# ---------------------------------------------------------------------------
ci: lint test ## Run the full CI pipeline (lint → test)

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
docker-build: ## Build Docker images
	docker compose -f infra/docker-compose.yml build

docker-up: ## Start services with Docker Compose
	docker compose -f infra/docker-compose.yml up --build

docker-down: ## Stop and remove containers
	docker compose -f infra/docker-compose.yml down

docker-logs: ## Tail logs from all services
	docker compose -f infra/docker-compose.yml logs -f

docker-prod-up: ## Start production stack
	docker compose -f infra/docker-compose.prod.yml up -d --build

docker-prod-down: ## Stop production stack
	docker compose -f infra/docker-compose.prod.yml down

# ---------------------------------------------------------------------------
# Database (Alembic)
# ---------------------------------------------------------------------------
migrate-up: ## Apply all pending migrations
	$(ALEMBIC) upgrade head

migrate-down: ## Rollback the last migration
	$(ALEMBIC) downgrade -1

migration: ## Create a new migration: make migration m="add review table"
	$(ALEMBIC) revision --autogenerate -m "$(m)"

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
clean: ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "coverage.xml" -delete
	rm -rf .venv/
	rm -rf *.egg-info/

bump-version: ## Bump version: make bump-version part=patch (major|minor|patch)
	$(eval PART := $(or $(part),patch))
	$(PYTHON) -c "
import re
with open('app/__init__.py') as f:
    content = f.read()
match = re.search(r\"__version__\s*=\s*['\\\"]([^'\\\"]+)['\\\"]\", content)
if not match:
    raise ValueError('Version not found')
major, minor, patch = map(int, match.group(1).split('.'))
if '$(PART)' == 'major': major, minor, patch = major+1, 0, 0
elif '$(PART)' == 'minor': minor, patch = minor+1, 0
else: patch += 1
new = f'{major}.{minor}.{patch}'
content = content.replace(match.group(0), f\"__version__ = '{new}'\")
with open('app/__init__.py', 'w') as f:
    f.write(content)
print(f'Bumped to {new}')
	"
	@echo "Don't forget to commit and tag: git tag v$$(grep __version__ app/__init__.py | grep -oP \"[\d\.]+\")"
