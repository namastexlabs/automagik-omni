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
SERVICE_NAME := omni-hub
SERVICE_FILE := /etc/systemd/system/$(SERVICE_NAME).service
SYSTEMCTL := systemctl

# Load environment variables from .env file if it exists
-include .env
export

# Default values (will be overridden by .env if present)
HOST ?= 127.0.0.1
PORT ?= 8000
LOG_LEVEL ?= info

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
	@echo ""
	@echo -e "$(FONT_PURPLE)                                                                                            $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)                                                                                            $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)     -+*         -=@%*@@@@@@*  -#@@@%*  =@@*      -%@#+   -*       +%@@@@*-%@*-@@*  -+@@*   $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)     =@#*  -@@*  -=@%+@@@@@@*-%@@#%*%@@+=@@@*    -+@@#+  -@@*   -#@@%%@@@*-%@+-@@* -@@#*    $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)    -%@@#* -@@*  -=@@* -@%* -@@**   --@@=@@@@*  -+@@@#+ -#@@%* -*@%*-@@@@*-%@+:@@+#@@*      $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)   -#@+%@* -@@*  -=@@* -@%* -@@*-+@#*-%@+@@=@@* +@%#@#+ =@##@* -%@#*-@@@@*-%@+-@@@@@*       $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)  -*@#==@@*-@@*  -+@%* -@%* -%@#*   -+@@=@@++@%-@@=*@#=-@@*-@@*:+@@*  -%@*-%@+-@@#*@@**     $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)  -@@* -+@%-+@@@@@@@*  -@%*  -#@@@@%@@%+=@@+-=@@@*    -%@*  -@@*-*@@@@%@@*#@@#=%*  -%@@*    $(FONT_RESET)"
	@echo -e "$(FONT_PURPLE) -@@*+  -%@*  -#@%+    -@%+     =#@@*   =@@+          +@%+  -#@#   -*%@@@*@@@@%+     =@@+   $(FONT_RESET)"
	@echo ""
endef

define check_prerequisites
	@if ! command -v uv >/dev/null 2>&1; then \
		$(call print_error,Missing uv package manager); \
		echo -e "$(FONT_YELLOW)💡 Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh$(FONT_RESET)"; \
		exit 1; \
	fi
	@if ! command -v python3 >/dev/null 2>&1; then \
		$(call print_error,Missing python3); \
		exit 1; \
	fi
endef

define ensure_env_file
	@if [ ! -f ".env" ]; then \
		cp .env.example .env 2>/dev/null || touch .env; \
		$(call print_info,.env file created); \
	fi
endef

define check_service_status
	@if systemctl is-active --quiet $(SERVICE_NAME); then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Service $(SERVICE_NAME) is running$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)   Status: $$(systemctl is-active $(SERVICE_NAME))$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)   Since:  $$(systemctl show $(SERVICE_NAME) --property=ActiveEnterTimestamp --value | cut -d' ' -f2-3)$(FONT_RESET)"; \
	elif systemctl is-enabled --quiet $(SERVICE_NAME); then \
		echo -e "$(FONT_YELLOW)$(WARNING) Service $(SERVICE_NAME) is enabled but not running$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_RED)$(ERROR) Service $(SERVICE_NAME) is not installed or enabled$(FONT_RESET)"; \
	fi
endef

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
	@echo -e "  $(FONT_GREEN)install-service$(FONT_RESET) Install systemd service"
	@echo -e "  $(FONT_GREEN)start-service  $(FONT_RESET) Start the systemd service"
	@echo -e "  $(FONT_GREEN)stop-service   $(FONT_RESET) Stop the systemd service"
	@echo -e "  $(FONT_GREEN)restart-service$(FONT_RESET) Restart the systemd service"
	@echo -e "  $(FONT_GREEN)service-status $(FONT_RESET) Check service status"
	@echo -e "  $(FONT_GREEN)logs           $(FONT_RESET) Show service logs (follow)"
	@echo -e "  $(FONT_GREEN)logs-tail      $(FONT_RESET) Show recent service logs"
	@echo ""
	@echo -e "$(FONT_BOLD)Database & CLI:$(FONT_RESET)"
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
# 🏗️ Development Commands
# ===========================================
.PHONY: install
install: ## Install project dependencies
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Installing dependencies with uv)
	@$(UV) sync
	$(call print_success_with_logo,Dependencies installed successfully)

.PHONY: dev
dev: ## Start development server with auto-reload
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Starting development server with auto-reload)
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs) && \
		$(UV) run uvicorn src.api.app:app --host $${API_HOST:-127.0.0.1} --port $${API_PORT:-8000} --reload --log-level $$(echo "$${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]'); \
	else \
		$(UV) run uvicorn src.api.app:app --host $(HOST) --port $(PORT) --reload --log-level $(shell echo "$(LOG_LEVEL)" | tr '[:upper:]' '[:lower:]'); \
	fi

.PHONY: test
test: ## Run the test suite
	$(call check_prerequisites)
	$(call print_status,Running test suite)
	@$(UV) run pytest tests/ -v --tb=short
	$(call print_success,Tests completed)

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	$(call check_prerequisites)
	$(call print_status,Running tests with coverage)
	@$(UV) run pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	$(call print_info,Coverage report generated in htmlcov/)

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
# 🔧 Service Management
# ===========================================
.PHONY: install-service
install-service: ## Install systemd service
	$(call print_status,Installing systemd service)
	@if [ ! -f "$(SERVICE_FILE)" ]; then \
		sudo tee $(SERVICE_FILE) > /dev/null << 'EOF'; \
[Unit]; \
Description=Omni-Hub Multi-Tenant WhatsApp Agent Service; \
After=network.target; \
Wants=network.target; \
; \
[Service]; \
Type=simple; \
User=$(USER); \
WorkingDirectory=$(PROJECT_ROOT); \
Environment=PATH=$(PROJECT_ROOT)/.venv/bin:$(PATH); \
ExecStart=$(PROJECT_ROOT)/.venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000; \
Restart=always; \
RestartSec=10; \
StandardOutput=journal; \
StandardError=journal; \
; \
[Install]; \
WantedBy=multi-user.target; \
EOF \
		sudo systemctl daemon-reload; \
		sudo systemctl enable $(SERVICE_NAME); \
		$(call print_success_with_logo,Service installed and enabled); \
	else \
		$(call print_warning,Service already installed); \
	fi

.PHONY: start-service
start-service: ## Start the systemd service
	$(call print_status,Starting $(SERVICE_NAME) service)
	@sudo systemctl start $(SERVICE_NAME)
	@sleep 2
	$(call check_service_status)

.PHONY: stop-service
stop-service: ## Stop the systemd service
	$(call print_status,Stopping $(SERVICE_NAME) service)
	@sudo systemctl stop $(SERVICE_NAME)
	$(call print_success,Service stopped)

.PHONY: restart-service
restart-service: ## Restart the systemd service
	$(call print_status,Restarting $(SERVICE_NAME) service)
	@sudo systemctl restart $(SERVICE_NAME)
	@sleep 2
	$(call check_service_status)

.PHONY: service-status
service-status: ## Check service status
	$(call print_status,Checking $(SERVICE_NAME) service status)
	$(call check_service_status)

.PHONY: logs
logs: ## Show service logs (follow)
	$(call print_status,Following $(SERVICE_NAME) logs)
	@sudo journalctl -u $(SERVICE_NAME) -f --no-pager

.PHONY: logs-tail
logs-tail: ## Show recent service logs
	$(call print_status,Recent $(SERVICE_NAME) logs)
	@sudo journalctl -u $(SERVICE_NAME) -n 50 --no-pager

# ===========================================
# 🗃️ Database & CLI Management
# ===========================================
.PHONY: db-init
db-init: ## Initialize database with default instance
	$(call check_prerequisites)
	$(call print_status,Initializing database)
	@$(UV) run python -c "from src.db.bootstrap import bootstrap_default_instance; bootstrap_default_instance()"
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
.PHONY: build
build: ## Build the project
	$(call check_prerequisites)
	$(call print_status,Building project)
	@$(UV) build
	$(call print_success,Build completed)

.PHONY: publish-test
publish-test: ## Publish to Test PyPI
	$(call check_prerequisites)
	$(call print_status,Publishing to Test PyPI)
	@$(UV) publish --repository testpypi
	$(call print_success,Published to Test PyPI)

.PHONY: publish
publish: ## Publish to PyPI
	$(call check_prerequisites)
	$(call print_status,Publishing to PyPI)
	@$(UV) publish
	$(call print_success,Published to PyPI)

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
uninstall-service: ## Uninstall systemd service
	$(call print_status,Uninstalling systemd service)
	@if [ -f "$(SERVICE_FILE)" ]; then \
		sudo systemctl stop $(SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(SERVICE_NAME) 2>/dev/null || true; \
		sudo rm -f $(SERVICE_FILE); \
		sudo systemctl daemon-reload; \
		$(call print_success,Service uninstalled); \
	else \
		$(call print_warning,Service not found); \
	fi

# ===========================================
# 🚀 Quick Commands
# ===========================================
.PHONY: up
up: install dev ## Quick start: install + dev server

.PHONY: check
check: quality test ## Quick check: quality + tests

.PHONY: deploy-service
deploy-service: install install-service start-service ## Deploy as service: install + service + start
	$(call print_success_with_logo,Omni-Hub deployed as service and ready!)

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
	@echo ""
	$(call check_service_status)
	@echo ""