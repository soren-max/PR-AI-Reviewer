# =============================================================================
# AI PR Review — Makefile
# =============================================================================
.PHONY: help backend frontend dev lint test typecheck clean docker-up docker-down

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
backend-install: ## Install backend dependencies
	cd backend && pip install -r requirements-dev.txt

backend-dev: ## Start backend in development mode
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

backend-test: ## Run backend tests
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

backend-lint: ## Lint backend code
	cd backend && ruff check app/ tests/

backend-typecheck: ## Type-check backend code
	cd backend && mypy app/ --strict --ignore-missing-imports

backend-format: ## Format backend code
	cd backend && ruff format app/ tests/

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-dev: ## Start frontend in development mode
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npm run build

frontend-lint: ## Lint frontend code
	cd frontend && npm run lint

frontend-typecheck: ## Type-check frontend code
	cd frontend && npm run typecheck

# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------
install: backend-install frontend-install ## Install all dependencies

dev: ## Start both backend and frontend in dev mode
	@echo "Starting backend and frontend..." && \
	trap 'kill 0' INT; \
	$(MAKE) backend-dev & \
	$(MAKE) frontend-dev & \
	wait

lint: backend-lint frontend-lint ## Lint all code

typecheck: backend-typecheck frontend-typecheck ## Type-check all code

test: backend-test ## Run all tests

ci: lint typecheck test ## Full CI pipeline

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
docker-up: ## Start development environment with Docker Compose
	docker compose -f infra/docker-compose.yml up --build

docker-down: ## Stop Docker Compose
	docker compose -f infra/docker-compose.yml down

docker-prod-up: ## Start production environment
	docker compose -f infra/docker-compose.prod.yml up -d --build

docker-prod-down: ## Stop production environment
	docker compose -f infra/docker-compose.prod.yml down

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/.next frontend/node_modules
	rm -rf backend/data/*.db
