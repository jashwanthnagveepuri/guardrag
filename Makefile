# =============================================================================
# GuardRAG — Makefile for Common Development Tasks
# =============================================================================

.PHONY: help setup build up down logs test lint format typecheck db-migrate db-reset clean

# Default target
help: ## Show this help message
	@echo "GuardRAG — Available Commands"
	@echo "=============================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup & Installation
# ---------------------------------------------------------------------------

setup: ## One-command setup: create .env, build images, start services
	@echo "🚀 Setting up GuardRAG..."
	@if [ ! -f .env ]; then cp .env.template .env; echo "✅ Created .env from template"; fi
	@echo "⚠️  Please edit .env and add your OpenAI API key"
	@echo "🔨 Building Docker images..."
	docker compose build
	@echo "✅ Setup complete. Run 'make up' to start services."

install: ## Install Python dependencies locally (for development)
	poetry install --with dev

cd web && npm install

# ---------------------------------------------------------------------------
# Docker Operations
# ---------------------------------------------------------------------------

build: ## Build all Docker images
	docker compose build

up: ## Start all services in detached mode
	docker compose up -d

down: ## Stop all services
	docker compose down

down-volumes: ## Stop all services and remove volumes (⚠️ destroys data)
	docker compose down -v

logs: ## Show logs from all services
	docker compose logs -f

logs-api: ## Show API logs only
	docker compose logs -f api

ps: ## Show running containers
	docker compose ps

# ---------------------------------------------------------------------------
# Development Server (local)
# ---------------------------------------------------------------------------

dev-api: ## Run API with hot reload (requires Poetry + local DB)
	poetry run uvicorn guardrag.api.main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Run frontend dev server
	cd web && npm run dev

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run all tests with coverage report
	poetry run pytest -v --tb=short --cov=guardrag --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without coverage (faster)
	poetry run pytest -v --tb=short

test-api: ## Run API route tests only
	poetry run pytest tests/test_api/ -v --tb=short

test-services: ## Run service unit tests only
	poetry run pytest tests/test_services/ -v --tb=short

test-watch: ## Run tests in watch mode
	poetry run pytest -v -f --tb=short

# ---------------------------------------------------------------------------
# Code Quality
# ---------------------------------------------------------------------------

lint: ## Run ruff linter
	poetry run ruff check guardrag/ tests/

lint-fix: ## Run ruff linter with auto-fix
	poetry run ruff check --fix guardrag/ tests/

format: ## Format code with ruff
	poetry run ruff format guardrag/ tests/

typecheck: ## Run mypy type checker
	poetry run mypy guardrag/

qa: lint typecheck test ## Run all quality checks (lint + typecheck + test)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

db-migrate: ## Run database migrations
	poetry run alembic upgrade head

db-reset: ## Reset database (drop all tables and re-migrate) ⚠️
	@echo "⚠️  This will destroy all data in the database!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	poetry run alembic downgrade base
	poetry run alembic upgrade head

db-shell: ## Open PostgreSQL shell in the container
	docker compose exec postgres psql -U guardrag -d guardrag

# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

guardrail-scan: ## Scan text via guardrail (usage: make guardrail-scan TEXT="your text")
	@curl -s -X POST http://localhost/api/v1/guardrails/scan \
		-H "Content-Type: application/json" \
		-d "{\"text\": \"$${TEXT}\"}" | python -m json.tool

guardrail-stats: ## Get guardrail statistics
	@curl -s http://localhost/api/v1/guardrails/stats | python -m json.tool

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

clean: ## Clean build artifacts and caches
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

clean-all: clean ## Clean everything including Docker volumes ⚠️
	docker compose down -v 2>/dev/null || true
	docker system prune -f 2>/dev/null || true

health: ## Check system health
	@curl -s http://localhost/health | python -m json.tool

stats: ## Get system statistics
	@curl -s http://localhost/api/stats | python -m json.tool

# ---------------------------------------------------------------------------
# CI/CD Simulation
# ---------------------------------------------------------------------------

ci: build ## Simulate CI pipeline locally
	@echo "🔍 Running CI pipeline simulation..."
	poetry run ruff check guardrag/ tests/
	poetry run mypy guardrag/
	poetry run pytest -v --tb=short --cov=guardrag --cov-fail-under=80
	@echo "✅ CI simulation passed!"
