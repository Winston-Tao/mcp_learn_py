# Makefile for MCP Learning Server

.PHONY: help install install-dev test lint format clean build run run-http run-docker deploy-dev deploy-prod backup logs shell

# Default target
help: ## Show this help message
	@echo "MCP Learning Server - Available Commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Development setup
install: ## Install production dependencies
	uv sync

install-dev: ## Install development dependencies
	uv sync --dev

# Code quality
test: ## Run tests
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint: ## Run linting checks
	uv run flake8 src/ tests/
	uv run mypy src/

format: ## Format code
	uv run black src/ tests/
	uv run isort src/ tests/

format-check: ## Check code formatting
	uv run black --check src/ tests/
	uv run isort --check-only src/ tests/

# Development server
run: ## Run server with STDIO transport
	uv run python scripts/start_server.py

run-http: ## Run server with HTTP transport
	uv run python scripts/start_server.py --transport http --port 8000

run-debug: ## Run server in debug mode
	uv run python scripts/start_server.py --transport http --debug

# Docker operations
build: ## Build Docker image
	docker build -t mcp-learning-server:latest .

run-docker: ## Run server in Docker container
	docker run --rm -p 8000:8000 --name mcp-server mcp-learning-server:latest

# Testing with test client
test-client: ## Run interactive test client
	uv run python scripts/test_client.py --interactive

test-client-auto: ## Run automated test client
	uv run python scripts/test_client.py

# Docker Compose operations
up: ## Start all services with docker-compose
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

logs-server: ## Show logs from MCP server only
	docker-compose logs -f mcp-server

restart: ## Restart all services
	docker-compose restart

# Deployment
deploy-dev: ## Deploy to development environment
	./scripts/deploy.sh development

deploy-prod: ## Deploy to production environment
	./scripts/deploy.sh production --test

# Backup and maintenance
backup: ## Create backup
	./scripts/backup.sh

clean: ## Clean up build artifacts and cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/

clean-docker: ## Clean up Docker images and containers
	docker-compose down --volumes --remove-orphans
	docker system prune -f
	docker image prune -f

# Utility commands
shell: ## Open shell in running container
	docker-compose exec mcp-server /bin/bash

psql: ## Connect to PostgreSQL (if running)
	docker-compose exec postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB

redis-cli: ## Connect to Redis CLI (if running)
	docker-compose exec redis redis-cli

# Environment setup
env: ## Copy .env.example to .env
	cp .env.example .env
	@echo "Created .env file. Please edit it with your configuration."

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "Documentation is available in docs/ directory"
	@echo "- docs/deployment.md - Deployment guide"
	@echo "- docs/api_reference.md - API reference"
	@echo "- README.md - Main documentation"

# Security scan (requires additional tools)
security-scan: ## Run security scans
	@echo "Running security scans..."
	@if command -v safety >/dev/null 2>&1; then \
		uv run safety check; \
	else \
		echo "Install 'safety' for dependency security scanning: pip install safety"; \
	fi
	@if command -v bandit >/dev/null 2>&1; then \
		uv run bandit -r src/; \
	else \
		echo "Install 'bandit' for code security scanning: pip install bandit"; \
	fi

# Pre-commit setup
pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

# All-in-one commands
check: format-check lint test ## Run all code quality checks

prepare: clean install-dev format lint test ## Prepare development environment

ci: format-check lint test ## Run CI pipeline checks locally

# Release preparation
version: ## Show current version
	@grep -E '^version = ' pyproject.toml | cut -d'"' -f2

# Health checks
health: ## Check server health
	@curl -f http://localhost:8000/health && echo "\nServer is healthy!" || echo "\nServer health check failed!"

status: ## Show service status
	docker-compose ps