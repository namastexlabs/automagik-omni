# ===========================================
# 🪄 Omni-Hub - Streamlined Makefile
# ===========================================

.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash

# ===========================================
# 🎨 Colors & Symbols
# ===========================================
FONT_RED := $(shell tput setaf 1)
FONT_GREEN := $(shell tput setaf 2)
FONT_YELLOW := $(shell tput setaf 3)
FONT_BLUE := $(shell tput setaf 4)
FONT_PURPLE := $(shell tput setaf 5)
FONT_CYAN := $(shell tput setaf 6)
FONT_GRAY := $(shell tput setaf 7)
FONT_BLACK := $(shell tput setaf 8)
FONT_BOLD := $(shell tput bold)
FONT_RESET := $(shell tput sgr0)
CHECKMARK := ✅
WARNING := ⚠️
ERROR := ❌
ROCKET := 🚀
MAGIC := 🪄
HUB := 🔗
INFO := ℹ️
SPARKLES := ✨

# ===========================================
# 📁 Paths & Configuration
# ===========================================
PROJECT_ROOT := $(shell pwd)
PYTHON := python3
UV := uv
SERVICE_NAME := automagik-omni

# Load environment variables from .env file if it exists
-include .env
export

# Default values (will be overridden by .env if present)
AUTOMAGIK_OMNI_API_HOST ?= 0.0.0.0
AUTOMAGIK_OMNI_API_PORT ?= 8882
LOG_LEVEL ?= INFO

# ===========================================
# 🛠️ Utility Functions
# ===========================================
define print_status
	@echo -e "$(FONT_PURPLE)$(HUB) $(1)$(FONT_RESET)"
endef

define print_success
	@echo -e "$(FONT_GREEN)$(CHECKMARK) $(1)$(FONT_RESET)"
endef

define print_warning
	@echo -e "$(FONT_YELLOW)$(WARNING) $(1)$(FONT_RESET)"
endef

define print_error
	@echo -e "$(FONT_RED)$(ERROR) $(1)$(FONT_RESET)"
endef

define print_info
	@echo -e "$(FONT_CYAN)$(INFO) $(1)$(FONT_RESET)"
endef

define print_success_with_logo
	@echo -e "$(FONT_GREEN)$(CHECKMARK) $(1)$(FONT_RESET)"
	@$(call show_automagik_logo)
endef

define show_automagik_logo
	[ -z "$$AUTOMAGIK_QUIET_LOGO" ] && { \
		echo ""; \
		echo -e "$(FONT_PURPLE)                                                                                            $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)                                                                                            $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)     -+*         -=@%*@@@@@@*  -#@@@%*  =@@*      -%@#+   -*       +%@@@@*-%@*-@@*  -+@@*   $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)     =@#*  -@@*  -=@%+@@@@@@*-%@@#%*%@@+=@@@*    -+@@#+  -@@*   -#@@%%@@@*-%@+-@@* -@@#*    $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)    -%@@#* -@@*  -=@@* -@%* -@@**   --@@=@@@@*  -+@@@#+ -#@@%* -*@%*-@@@@*-%@+:@@+#@@*      $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)   -#@+%@* -@@*  -=@@* -@%* -@@*-+@#*-%@+@@=@@* +@%#@#+ =@##@* -%@#*-@@@@*-%@+-@@@@@*       $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)  -*@#==@@*-@@*  -+@%* -@%* -%@#*   -+@@=@@++@%-@@=*@#=-@@*-@@*:+@@*  -%@*-%@+-@@#*@@**     $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE)  -@@* -+@%-+@@@@@@@*  -@%*  -#@@@@%@@%+=@@+-=@@@*    -%@*  -@@*-*@@@@%@@*#@@#=%*  -%@@*    $(FONT_RESET)"; \
		echo -e "$(FONT_PURPLE) -@@*+  -%@*  -#@%+    -@%+     =#@@*   =@@+          +@%+  -#@#   -*%@@@*@@@@%+     =@@+   $(FONT_RESET)"; \
		echo ""; \
	} || true
endef

define check_prerequisites
	@if ! command -v uv >/dev/null 2>&1; then \
		echo -e "$(FONT_RED)$(ERROR) Missing uv package manager$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)💡 Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh$(FONT_RESET)"; \
		exit 1; \
	fi
	@if ! command -v python3 >/dev/null 2>&1; then \
		echo -e "$(FONT_RED)$(ERROR) Missing python3$(FONT_RESET)"; \
		exit 1; \
	fi
endef

define check_pm2
	@if ! command -v pm2 >/dev/null 2>&1; then \
		echo -e "$(FONT_RED)$(ERROR) PM2 not found. Install with: npm install -g pm2$(FONT_RESET)"; \
		exit 1; \
	fi
endef

define ensure_env_file
	@if [ ! -f ".env" ]; then \
		cp .env.example .env 2>/dev/null || touch .env; \
		echo -e "$(FONT_CYAN)$(INFO) .env file created$(FONT_RESET)"; \
	fi
endef

# Function removed - now using PM2 for service management

# ===========================================
# 📋 Help System
# ===========================================
.PHONY: help
help: ## Show this help message
	@echo ""
	@echo -e "$(FONT_PURPLE)$(HUB) Omni-Hub Development & Deployment Commands$(FONT_RESET)"
	@echo ""
	@echo -e "$(FONT_BOLD)Development:$(FONT_RESET)"
	@echo -e "  $(FONT_CYAN)install        $(FONT_RESET) Install project dependencies"
	@echo -e "  $(FONT_CYAN)dev            $(FONT_RESET) Start development server with auto-reload"
	@echo -e "  $(FONT_CYAN)test           $(FONT_RESET) Run the test suite"
	@echo -e "  $(FONT_CYAN)test-coverage  $(FONT_RESET) Run tests with coverage report"
	@echo -e "  $(FONT_CYAN)lint           $(FONT_RESET) Run code linting with ruff"
	@echo -e "  $(FONT_CYAN)lint-fix       $(FONT_RESET) Fix auto-fixable linting issues"
	@echo -e "  $(FONT_CYAN)format         $(FONT_RESET) Format code with black"
	@echo -e "  $(FONT_CYAN)typecheck      $(FONT_RESET) Run type checking with mypy"
	@echo -e "  $(FONT_CYAN)quality        $(FONT_RESET) Run all code quality checks"
	@echo ""
	@echo -e "$(FONT_BOLD)Service Management:$(FONT_RESET)"
	@echo -e "  $(FONT_GREEN)start-local    $(FONT_RESET) Start local PM2 service"
	@echo -e "  $(FONT_GREEN)stop-local     $(FONT_RESET) Stop local PM2 service"
	@echo -e "  $(FONT_GREEN)restart-local  $(FONT_RESET) Restart local PM2 service"
	@echo -e "  $(FONT_GREEN)status-local   $(FONT_RESET) Check local PM2 service status"
	@echo -e "  $(FONT_GREEN)logs-local     $(FONT_RESET) Show local PM2 service logs"
	@echo -e "  $(FONT_GREEN)logs-follow-local$(FONT_RESET) Follow local PM2 service logs"
	@echo -e "  $(FONT_GREEN)install-service$(FONT_RESET) Install service (delegates to local PM2)"
	@echo -e "  $(FONT_GREEN)start-service  $(FONT_RESET) Start service (delegates to local PM2)"
	@echo -e "  $(FONT_GREEN)stop-service   $(FONT_RESET) Stop service (delegates to local PM2)"
	@echo -e "  $(FONT_GREEN)restart-service$(FONT_RESET) Restart service (delegates to local PM2)"
	@echo ""
	@echo -e "$(FONT_BOLD)Discord Bot Management:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)discord-start  $(FONT_RESET) Start Discord bot (INSTANCE=name)"
	@echo -e "  $(FONT_PURPLE)discord-stop   $(FONT_RESET) Stop Discord bot (INSTANCE=name)"  
	@echo -e "  $(FONT_PURPLE)discord-restart$(FONT_RESET) Restart Discord bot (INSTANCE=name)"
	@echo -e "  $(FONT_PURPLE)discord-status $(FONT_RESET) Show Discord bot status"
	@echo -e "  $(FONT_PURPLE)discord-logs   $(FONT_RESET) Show Discord service logs"
	@echo -e "  $(FONT_PURPLE)discord-list   $(FONT_RESET) List all Discord instances"
	@echo ""	@echo -e "$(FONT_BOLD)Database & CLI:$(FONT_RESET)"
	@echo -e "  $(FONT_YELLOW)db-init        $(FONT_RESET) Initialize database with default instance"
	@echo -e "  $(FONT_YELLOW)cli-instances  $(FONT_RESET) List all instances via CLI"
	@echo -e "  $(FONT_YELLOW)cli-create     $(FONT_RESET) Create new instance via CLI (interactive)"
	@echo -e "  $(FONT_YELLOW)validate       $(FONT_RESET) Run multi-tenancy validation"
	@echo ""
	@echo -e "$(FONT_BOLD)Publishing & Deployment:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)build          $(FONT_RESET) Build the project"
	@echo -e "  $(FONT_PURPLE)publish-test   $(FONT_RESET) Publish to Test PyPI"
	@echo -e "  $(FONT_PURPLE)publish        $(FONT_RESET) Publish to PyPI"
	@echo -e "  $(FONT_PURPLE)release        $(FONT_RESET) Full release process (quality + test + build)"
	@echo ""
	@echo -e "$(FONT_BOLD)Quick Commands:$(FONT_RESET)"
	@echo -e "  $(FONT_CYAN)up             $(FONT_RESET) Quick start: install + dev server"
	@echo -e "  $(FONT_CYAN)check          $(FONT_RESET) Quick check: quality + tests"
	@echo -e "  $(FONT_GREEN)deploy-service $(FONT_RESET) Deploy as service: install + service + start"
	@echo ""

# ===========================================
# 🎮 Discord Bot Management
# ===========================================
.PHONY: discord-start discord-stop discord-restart discord-status discord-logs discord-list

discord-start: ## Start Discord bot for specified instance
	@if [ -z "$(INSTANCE)" ]; then \
		echo "Usage: make discord-start INSTANCE=<instance-name>"; \
		exit 1; \
	fi
	@echo "Starting Discord bot for instance: $(INSTANCE)..."
	@uv run python -m src.cli.main_cli discord start $(INSTANCE)

discord-stop: ## Stop Discord bot for specified instance
	@if [ -z "$(INSTANCE)" ]; then \
		echo "Usage: make discord-stop INSTANCE=<instance-name>"; \
		exit 1; \
	fi
	@echo "Stopping Discord bot for instance: $(INSTANCE)..."
	@uv run python -m src.cli.main_cli discord stop $(INSTANCE)

discord-restart: ## Restart Discord bot for specified instance
	@if [ -z "$(INSTANCE)" ]; then \
		echo "Usage: make discord-restart INSTANCE=<instance-name>"; \
		exit 1; \
	fi
	@echo "Restarting Discord bot for instance: $(INSTANCE)..."
	@uv run python -m src.cli.main_cli discord restart $(INSTANCE)

discord-status: ## Show Discord bot status
	@echo "Discord bot status:"
	@if [ -n "$(INSTANCE)" ]; then \
		uv run python -m src.cli.main_cli discord status $(INSTANCE); \
	else \
		uv run python -m src.cli.main_cli discord status; \
	fi

discord-logs: ## Show Discord service logs
	@echo "Showing Discord service logs..."
	@pm2 logs automagik-omni-discord --lines 50

discord-list: ## List all Discord instances
	@echo "Available Discord instances:"
	@uv run python -m src.cli.main_cli discord list

# ===========================================
# 🏗️ Development Commands
# ===========================================
.PHONY: install
install: ## Install project dependencies
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Installing dependencies with uv)
	@if ! $(UV) sync 2>/dev/null; then \
		echo -e "$(FONT_YELLOW)$(WARNING) Installation failed - clearing UV cache and retrying...$(FONT_RESET)"; \
		$(UV) cache clean; \
		$(UV) sync; \
	fi
	$(call print_success_with_logo,Dependencies installed successfully)

.PHONY: dev
dev: ## Start development server with auto-reload
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Starting development server with auto-reload)
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs) && \
		$(UV) run python -m uvicorn src.api.app:app --host $${AUTOMAGIK_OMNI_API_HOST:-0.0.0.0} --port $${AUTOMAGIK_OMNI_API_PORT:-8882} --reload --workers 1 --log-level $$(echo "$${LOG_LEVEL:-INFO}" | tr '[:upper:]' '[:lower:]'); \
	else \
		$(UV) run python -m uvicorn src.api.app:app --host $(AUTOMAGIK_OMNI_API_HOST) --port $(AUTOMAGIK_OMNI_API_PORT) --reload --workers 1 --log-level $(shell echo "$(LOG_LEVEL)" | tr '[:upper:]' '[:lower:]'); \
	fi

.PHONY: test
test: ## Run the test suite (auto-detects database)
	$(call check_prerequisites)
	$(call print_status,Running test suite)
	@$(UV) run pytest tests/ -v --tb=short
	$(call print_success,Tests completed)

.PHONY: test-coverage
test-coverage: ## Run tests with detailed coverage report (HTML + terminal)
	$(call check_prerequisites)
	$(call print_status,Running tests with coverage)
	@$(UV) run pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-report=term:skip-covered
	$(call print_info,Coverage report generated in htmlcov/)
	$(call print_info,Open htmlcov/index.html in browser to view detailed report)

.PHONY: test-coverage-summary
test-coverage-summary: ## Show coverage summary only
	$(call check_prerequisites)
	$(call print_status,Running coverage summary)
	@$(UV) run pytest tests/ --cov=src --cov-report=term --tb=no -q
	$(call print_success,Coverage summary completed)

.PHONY: test-postgres
test-postgres: ## Run tests with PostgreSQL (requires Docker or local PostgreSQL)
	$(call check_prerequisites)
	$(call print_status,Setting up PostgreSQL for testing)
	@if [ -z "$$POSTGRES_HOST" ]; then \
		echo "$(FONT_YELLOW)$(WARNING) POSTGRES_HOST not set, using setup script...$(FONT_RESET)"; \
		./scripts/setup-test-postgres.sh; \
	fi
	@POSTGRES_HOST=$${POSTGRES_HOST:-localhost} $(UV) run pytest tests/ -v --tb=short
	$(call print_success,PostgreSQL tests completed)

.PHONY: test-postgres-setup
test-postgres-setup: ## Setup PostgreSQL test environment with Docker
	$(call print_status,Setting up PostgreSQL test environment)
	@./scripts/setup-test-postgres.sh
	$(call print_success,PostgreSQL test environment ready)

.PHONY: test-postgres-teardown
test-postgres-teardown: ## Stop and remove PostgreSQL test container
	$(call print_status,Tearing down PostgreSQL test environment)
	@./scripts/setup-test-postgres.sh stop
	@./scripts/setup-test-postgres.sh remove
	$(call print_success,PostgreSQL test environment removed)

.PHONY: test-sqlite
test-sqlite: ## Force tests to use SQLite (override PostgreSQL if set)
	$(call check_prerequisites)
	$(call print_status,Running tests with SQLite)
	@unset POSTGRES_HOST POSTGRES_PORT POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB TEST_DATABASE_URL && \
	$(UV) run pytest tests/ -v --tb=short
	$(call print_success,SQLite tests completed)

.PHONY: lint
lint: ## Run code linting with ruff
	$(call check_prerequisites)
	$(call print_status,Running ruff linter)
	@$(UV) run ruff check src/ tests/
	$(call print_success,Linting completed)

.PHONY: lint-fix
lint-fix: ## Fix auto-fixable linting issues
	$(call check_prerequisites)
	$(call print_status,Fixing linting issues with ruff)
	@$(UV) run ruff check src/ tests/ --fix
	$(call print_success,Auto-fixable issues resolved)

.PHONY: format
format: ## Format code with black
	$(call check_prerequisites)
	$(call print_status,Formatting code with black)
	@$(UV) run black src/ tests/
	$(call print_success,Code formatted)

.PHONY: typecheck
typecheck: ## Run type checking with mypy
	$(call check_prerequisites)
	$(call print_status,Running type checks with mypy)
	@$(UV) run mypy src/
	$(call print_success,Type checking completed)

.PHONY: quality
quality: lint typecheck ## Run all code quality checks
	$(call print_success,All quality checks completed)

# ===========================================
# 🔧 Local PM2 Management
# ===========================================
.PHONY: setup-pm2 start-local stop-local restart-local status-local logs-local logs-follow-local

setup-pm2: ## Setup local PM2 ecosystem
	$(call print_status,Setting up local PM2 ecosystem)
	@if [ ! -f "ecosystem.config.js" ]; then \
		$(call print_error,ecosystem.config.js not found in current directory); \
		exit 1; \
	fi
	@$(call check_pm2)
	@$(call print_success,PM2 ecosystem ready)

start-local: setup-pm2 ## Start local PM2 service
	$(call print_status,Starting local PM2 service)
	@pm2 start ecosystem.config.js 2>/dev/null || pm2 restart automagik-omni
	@pm2 save
	@$(call print_success,Local PM2 service started)

stop-local: ## Stop local PM2 service
	$(call print_status,Stopping local PM2 service)
	@$(call check_pm2)
	@pm2 stop automagik-omni 2>/dev/null || true
	@$(call print_success,Local PM2 service stopped)

restart-local: ## Restart local PM2 service
	$(call print_status,Restarting local PM2 service)
	@$(call check_pm2)
	@pm2 restart automagik-omni 2>/dev/null || pm2 start ecosystem.config.js
	@$(call print_success,Local PM2 service restarted)

status-local: ## Check local PM2 service status
	$(call print_status,Checking local PM2 service status)
	@$(call check_pm2)
	@pm2 show automagik-omni 2>/dev/null || echo "Service not running"

logs-local: ## Show local PM2 service logs
	$(eval N := $(or $(N),30))
	$(call print_status,Recent logs)
	@pm2 logs automagik-omni --lines $(N) --nostream 2>/dev/null || echo "No logs available"

logs-follow-local: ## Follow local PM2 service logs
	$(call print_status,Following logs - Press Ctrl+C to stop)
	@pm2 logs automagik-omni 2>/dev/null || echo "No logs available"

# ===========================================
# 🔧 Service Management (Delegates to Local PM2)
# ===========================================
.PHONY: install-service start-service stop-service restart-service service-status logs logs-follow

install-service: start-local ## Install service (delegates to local PM2)

start-service: start-local ## Start service (delegates to local PM2)

stop-service: stop-local ## Stop service (delegates to local PM2)

restart-service: restart-local ## Restart service (delegates to local PM2)

service-status: status-local ## Check service status (delegates to local PM2)

logs: logs-local ## Show service logs (delegates to local PM2)

logs-follow: logs-follow-local ## Follow service logs (delegates to local PM2)

# ===========================================
# 🗃️ Database & CLI Management
# ===========================================
.PHONY: db-init
db-init: ## Initialize database with default instance
	$(call check_prerequisites)
	$(call print_status,Initializing database)
	@$(UV) run python -c "from src.db.bootstrap import ensure_default_instance; from src.db.database import SessionLocal; db = SessionLocal(); ensure_default_instance(db); db.close()"
	$(call print_success,Database initialized with default instance)

.PHONY: cli-instances
cli-instances: ## List all instances via CLI
	$(call check_prerequisites)
	$(call print_status,Listing instances)
	@$(UV) run python -m src.cli.instance_cli list

.PHONY: cli-create
cli-create: ## Create new instance via CLI (interactive)
	$(call check_prerequisites)
	$(call print_status,Creating new instance)
	@$(UV) run python -m src.cli.instance_cli create

.PHONY: validate
validate: ## Run multi-tenancy validation
	$(call check_prerequisites)
	$(call print_status,Running validation checks)
	@$(UV) run python scripts/validate_multitenancy.py
	$(call print_success,Validation completed)

# ===========================================
# 📦 Publishing & Release
# ===========================================
# Duplicate targets removed - see Build & Publish section below

.PHONY: release
release: quality test build ## Full release process (quality + test + build)
	$(call print_success_with_logo,Release build ready)
	$(call print_info,Run 'make publish-test' or 'make publish' to deploy)

# ===========================================
# 🧹 Cleanup & Maintenance
# ===========================================
.PHONY: clean
clean: ## Clean build artifacts and cache
	$(call print_status,Cleaning build artifacts)
	@rm -rf dist/
	@rm -rf build/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@rm -rf htmlcov/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	$(call print_success,Cleanup completed)

.PHONY: uninstall-service
uninstall-service: stop-local ## Uninstall local PM2 service
	$(call print_status,Uninstalling local PM2 service)
	@$(call check_pm2)
	@pm2 delete automagik-omni 2>/dev/null || true
	@pm2 save --force
	@$(call print_success,Local PM2 service uninstalled)

# ===========================================
# 🚀 Quick Commands
# ===========================================
.PHONY: up
up: install dev ## Quick start: install + dev server

.PHONY: check
check: quality test ## Quick check: quality + tests

.PHONY: deploy-service
deploy-service: install start-local ## Deploy as service: install + local PM2 start
	$(call print_success_with_logo,Omni-Hub deployed as local service and ready!)

# ===========================================
# 📊 Status & Info
# ===========================================
.PHONY: info
info: ## Show project information
	@echo ""
	@echo -e "$(FONT_PURPLE)$(HUB) Omni-Hub Project Information$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)Project Root:$(FONT_RESET) $(PROJECT_ROOT)"
	@echo -e "$(FONT_CYAN)Python:$(FONT_RESET) $(shell python3 --version 2>/dev/null || echo 'Not found')"
	@echo -e "$(FONT_CYAN)UV:$(FONT_RESET) $(shell uv --version 2>/dev/null || echo 'Not found')"
	@echo -e "$(FONT_CYAN)Service:$(FONT_RESET) $(SERVICE_NAME)"
	@echo -e "$(FONT_CYAN)PM2:$(FONT_RESET) $(shell pm2 --version 2>/dev/null || echo 'Not found')"
	@echo ""

# ===========================================
# 📦 Build & Publish
# ===========================================
.PHONY: build publish-test publish check-dist check-release clean-build
.PHONY: bump-patch bump-minor bump-major bump-dev publish-dev finalize-version

build: clean-build ## 📦 Build package
	$(call print_status,Building package...)
	@uv build
	$(call print_success,Package built!)

check-dist: ## 🔍 Check package quality
	$(call print_status,Checking package quality...)
	@uv run twine check dist/*

check-release: ## 🔍 Check if ready for release (clean working directory)
	$(call print_status,Checking release readiness...)
	@# Check for uncommitted changes
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo -e "$(FONT_RED)$(ERROR) Uncommitted changes detected!$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)Please commit or stash your changes before publishing.$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Run: git status$(FONT_RESET)"; \
		exit 1; \
	fi
	@# Check if on main branch
	@CURRENT_BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$CURRENT_BRANCH" != "main" ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) Not on main branch (current: $$CURRENT_BRANCH)$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)It's recommended to publish from the main branch.$(FONT_RESET)"; \
		read -p "Continue anyway? [y/N] " -n 1 -r; \
		echo; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			exit 1; \
		fi; \
	fi
	@# Check if main branch is up to date with origin
	@git fetch origin main --quiet; \
	if [ "$$(git rev-parse HEAD)" != "$$(git rev-parse origin/main)" ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) Local main branch differs from origin/main$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)Consider pulling latest changes or pushing your commits.$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Run: git pull origin main$(FONT_RESET)"; \
		read -p "Continue anyway? [y/N] " -n 1 -r; \
		echo; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			exit 1; \
		fi; \
	fi
	$(call print_success,Ready for release!)

publish-test: build check-dist ## 🧪 Upload to TestPyPI
	$(call print_status,Publishing to TestPyPI...)
	@if [ -z "$(TESTPYPI_TOKEN)" ]; then \
		$(call print_error,TESTPYPI_TOKEN not set); \
		echo -e "$(FONT_YELLOW)💡 Get your TestPyPI token at: https://test.pypi.org/manage/account/token/$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)💡 Set with: export TESTPYPI_TOKEN=pypi-xxxxx$(FONT_RESET)"; \
		exit 1; \
	fi
	@uv run twine upload --repository testpypi dist/* -u __token__ -p "$(TESTPYPI_TOKEN)"
	$(call print_success,Published to TestPyPI!)

publish: ## 🚀 Push committed changes and create GitHub release (triggers automated PyPI publishing)
	$(call print_status,Publishing committed version changes...)
	@# Push commits first
	@echo -e "$(FONT_CYAN)Pushing commits to origin...$(FONT_RESET)"; \
	git push origin; \
	# Get version from pyproject.toml
	VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	echo -e "$(FONT_CYAN)Publishing version: v$$VERSION$(FONT_RESET)"; \
	if ! git tag | grep -q "^v$$VERSION$$"; then \
		echo -e "$(FONT_CYAN)Creating git tag v$$VERSION$(FONT_RESET)"; \
		git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	fi; \
	echo -e "$(FONT_CYAN)Pushing tag to GitHub$(FONT_RESET)"; \
	git push origin "v$$VERSION"; \
	if command -v gh >/dev/null 2>&1; then \
		echo -e "$(FONT_CYAN)Creating GitHub release$(FONT_RESET)"; \
		gh release create "v$$VERSION" \
			--title "v$$VERSION" \
			--notes "Release v$$VERSION - Automated PyPI publishing via GitHub Actions with Trusted Publisher" \
			--generate-notes || echo -e "$(FONT_YELLOW)$(WARNING) GitHub release creation failed (may already exist)$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) GitHub CLI (gh) not found - creating release manually$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Go to: https://github.com/namastexlabs/automagik-omni/releases/new$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Tag: v$$VERSION$(FONT_RESET)"; \
	fi; \
	echo -e "$(FONT_PURPLE)🚀 GitHub Actions will now build and publish to PyPI automatically!$(FONT_RESET)"; \
	echo -e "$(FONT_CYAN)Monitor progress: https://github.com/namastexlabs/automagik-omni/actions$(FONT_RESET)"
	$(call print_success,GitHub release created! PyPI publishing in progress...)

clean-build: ## 🧹 Clean build artifacts
	$(call print_status,Cleaning build artifacts...)
	@rm -rf build dist *.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	$(call print_success,Build artifacts cleaned!)

# ===========================================
# 📈 Version Management
# ===========================================
version: ## 📊 Show current version
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	echo -e "$(FONT_CYAN)Current version: $(FONT_BOLD)$$CURRENT_VERSION$(FONT_RESET)"

version-bump: ## 🔧 Bump version with script (usage: make version-bump TYPE=patch)
	$(call print_status,Bumping version...)
	@if [ -z "$(TYPE)" ]; then \
		echo -e "$(FONT_RED)$(ERROR) Please specify TYPE (major, minor, patch, or auto)$(FONT_RESET)"; \
		echo -e "$(FONT_GRAY)Usage: make version-bump TYPE=patch$(FONT_RESET)"; \
		exit 1; \
	fi
	@python scripts/bump-version.py $(TYPE)

bump-patch: ## 📈 Bump patch version (0.1.0 -> 0.1.1)
	$(call print_status,Bumping patch version...)
	@# Check if git status is clean
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo -e "$(FONT_RED)$(ERROR) Uncommitted changes detected!$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)Please commit or stash your changes before version bump.$(FONT_RESET)"; \
		exit 1; \
	fi
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. '{$$NF = $$NF + 1;} 1' | sed 's/ /./g'); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version bumped from $$CURRENT_VERSION to $$NEW_VERSION$(FONT_RESET)"; \
	git add pyproject.toml; \
	git commit -m "chore: bump patch version to $$NEW_VERSION"; \
	echo -e "$(FONT_GREEN)✅ Changes committed with semantic commit message$(FONT_RESET)"

bump-minor: ## 📈 Bump minor version (0.1.0 -> 0.2.0)
	$(call print_status,Bumping minor version...)
	@# Check if git status is clean
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo -e "$(FONT_RED)$(ERROR) Uncommitted changes detected!$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)Please commit or stash your changes before version bump.$(FONT_RESET)"; \
		exit 1; \
	fi
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. '{$$2 = $$2 + 1; $$3 = 0;} 1' | sed 's/ /./g'); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version bumped from $$CURRENT_VERSION to $$NEW_VERSION$(FONT_RESET)"; \
	git add pyproject.toml; \
	git commit -m "feat: bump minor version to $$NEW_VERSION"; \
	echo -e "$(FONT_GREEN)✅ Changes committed with semantic commit message$(FONT_RESET)"

bump-major: ## 📈 Bump major version (0.1.0 -> 1.0.0)
	$(call print_status,Bumping major version...)
	@# Check if git status is clean
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo -e "$(FONT_RED)$(ERROR) Uncommitted changes detected!$(FONT_RESET)"; \
		echo -e "$(FONT_YELLOW)Please commit or stash your changes before version bump.$(FONT_RESET)"; \
		exit 1; \
	fi
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. '{$$1 = $$1 + 1; $$2 = 0; $$3 = 0;} 1' | sed 's/ /./g'); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version bumped from $$CURRENT_VERSION to $$NEW_VERSION$(FONT_RESET)"; \
	git add pyproject.toml; \
	git commit -m "feat!: bump major version to $$NEW_VERSION"; \
	echo -e "$(FONT_GREEN)✅ Changes committed with semantic commit message$(FONT_RESET)"

bump-dev: ## 🧪 Create dev version (0.1.2 -> 0.1.2pre1, 0.1.2pre1 -> 0.1.2pre2)
	$(call print_status,Creating dev pre-release version...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	if echo "$$CURRENT_VERSION" | grep -q "pre"; then \
		BASE_VERSION=$$(echo "$$CURRENT_VERSION" | cut -d'p' -f1); \
		PRE_NUM=$$(echo "$$CURRENT_VERSION" | sed 's/.*pre\([0-9]*\)/\1/'); \
		NEW_PRE_NUM=$$((PRE_NUM + 1)); \
		NEW_VERSION="$${BASE_VERSION}pre$${NEW_PRE_NUM}"; \
	else \
		NEW_VERSION="$${CURRENT_VERSION}pre1"; \
	fi; \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Dev version created: $$CURRENT_VERSION → $$NEW_VERSION$(FONT_RESET)"; \
	echo -e "$(FONT_CYAN)💡 Ready for: make publish-dev$(FONT_RESET)"

publish-dev: build check-dist ## 🚀 Build and publish dev version to PyPI
	$(call print_status,Publishing dev version to PyPI...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	if ! echo "$$CURRENT_VERSION" | grep -q "pre"; then \
		$(call print_error,Not a dev version! Use 'make bump-dev' first); \
		echo -e "$(FONT_GRAY)Current version: $$CURRENT_VERSION$(FONT_RESET)"; \
		exit 1; \
	fi
	@if [ -z "$(PYPI_TOKEN)" ]; then \
		$(call print_error,PYPI_TOKEN not set); \
		echo -e "$(FONT_YELLOW)💡 Get your PyPI token at: https://pypi.org/manage/account/token/$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)💡 Set with: export PYPI_TOKEN=pypi-xxxxx$(FONT_RESET)"; \
		exit 1; \
	fi
	@echo -e "$(FONT_CYAN)🚀 Publishing $$CURRENT_VERSION to PyPI for beta testing...$(FONT_RESET)"
	@uv run twine upload dist/* -u __token__ -p "$(PYPI_TOKEN)"
	@echo -e "$(FONT_GREEN)✅ Dev version published to PyPI!$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)💡 Users can install with: pip install omni-hub==$$CURRENT_VERSION$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)💡 Or latest pre-release: pip install --pre omni-hub$(FONT_RESET)"

finalize-version: ## ✅ Remove 'pre' from version (0.1.2pre3 -> 0.1.2)
	$(call print_status,Finalizing version for release...)
	@CURRENT_VERSION=$$(grep "^version" pyproject.toml | cut -d'"' -f2); \
	if ! echo "$$CURRENT_VERSION" | grep -q "pre"; then \
		$(call print_error,Not a pre-release version!); \
		echo -e "$(FONT_GRAY)Current version: $$CURRENT_VERSION$(FONT_RESET)"; \
		exit 1; \
	fi; \
	FINAL_VERSION=$$(echo "$$CURRENT_VERSION" | cut -d'p' -f1); \
	sed -i "s/version = \"$$CURRENT_VERSION\"/version = \"$$FINAL_VERSION\"/" pyproject.toml; \
	echo -e "$(FONT_GREEN)✅ Version finalized: $$CURRENT_VERSION → $$FINAL_VERSION$(FONT_RESET)"; \
	echo -e "$(FONT_CYAN)💡 Ready for: make publish$(FONT_RESET)"