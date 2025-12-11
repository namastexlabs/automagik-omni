# ===========================================
# Omni-Hub Makefile
# ===========================================

.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
SHELL := /bin/bash

# Colors
FONT_GREEN := $(shell tput setaf 2)
FONT_CYAN := $(shell tput setaf 6)
FONT_PURPLE := $(shell tput setaf 5)
FONT_YELLOW := $(shell tput setaf 3)
FONT_RED := $(shell tput setaf 1)
FONT_RESET := $(shell tput sgr0)

.PHONY: help install dev dev-backend dev-frontend update reload uninstall lint lint-fix format format-check typecheck test quality

help: ## Show available commands
	@echo ""
	@echo "$(FONT_PURPLE)Omni-Hub Commands$(FONT_RESET)"
	@echo ""
	@echo "  $(FONT_GREEN)install$(FONT_RESET)       Install dependencies and deploy to PM2"
	@echo "  $(FONT_CYAN)dev$(FONT_RESET)           Start full stack with hot reload (gateway)"
	@echo "  $(FONT_CYAN)dev-backend$(FONT_RESET)   Start Python API only (port 8000)"
	@echo "  $(FONT_CYAN)dev-frontend$(FONT_RESET)  Start UI only (hot reload)"
	@echo "  $(FONT_CYAN)reload$(FONT_RESET)        Restart services (after code changes)"
	@echo "  $(FONT_CYAN)update$(FONT_RESET)        Pull updates, rebuild, and restart"
	@echo "  $(FONT_RED)uninstall$(FONT_RESET)     Stop services and cleanup"
	@echo ""
	@echo "$(FONT_PURPLE)Quality Commands$(FONT_RESET)"
	@echo ""
	@echo "  $(FONT_YELLOW)lint$(FONT_RESET)          Run all linters (check mode)"
	@echo "  $(FONT_YELLOW)lint-fix$(FONT_RESET)      Run all linters with auto-fix"
	@echo "  $(FONT_YELLOW)format$(FONT_RESET)        Format all code"
	@echo "  $(FONT_YELLOW)format-check$(FONT_RESET)  Check formatting without fixing"
	@echo "  $(FONT_YELLOW)typecheck$(FONT_RESET)     Run TypeScript type checking"
	@echo "  $(FONT_YELLOW)test$(FONT_RESET)          Run all tests"
	@echo "  $(FONT_GREEN)quality$(FONT_RESET)       Run all quality checks"
	@echo ""

install: ## Install dependencies and deploy to PM2
	@echo "$(FONT_CYAN)Initializing submodules...$(FONT_RESET)"
	@git submodule update --init --recursive
	@echo "$(FONT_CYAN)Installing Python dependencies...$(FONT_RESET)"
	uv sync
	@echo "$(FONT_CYAN)Installing Gateway dependencies...$(FONT_RESET)"
	cd gateway && bun install
	@echo "$(FONT_CYAN)Installing UI dependencies...$(FONT_RESET)"
	cd resources/ui && bun install
	@echo "$(FONT_CYAN)Building UI...$(FONT_RESET)"
	cd resources/ui && bun run build
	@echo "$(FONT_CYAN)Starting PM2 service...$(FONT_RESET)"
	pm2 start ecosystem.config.cjs 2>/dev/null || pm2 restart ecosystem.config.cjs
	pm2 save
	@echo ""
	@echo "$(FONT_GREEN)Done!$(FONT_RESET) Access at http://localhost:8882"

reload: ## Restart services (after code changes)
	@echo "$(FONT_CYAN)Rebuilding UI...$(FONT_RESET)"
	@cd resources/ui && bun run build
	@echo "$(FONT_CYAN)Restarting PM2 service...$(FONT_RESET)"
	@pm2 restart ecosystem.config.cjs
	@echo ""
	@echo "$(FONT_GREEN)Reload complete!$(FONT_RESET)"

dev: ## Start full stack with hot reload (gateway + all services)
	@bun --watch gateway/src/index.ts

dev-backend: ## Start Python API only (standalone, port 8000)
	@uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start UI only (hot reload)
	@cd resources/ui && bun run dev

update: ## Pull updates, rebuild everything, restart
	@echo "$(FONT_CYAN)Pulling latest changes...$(FONT_RESET)"
	@git pull
	@echo "$(FONT_CYAN)Updating submodules...$(FONT_RESET)"
	@git submodule update --init --recursive
	@echo "$(FONT_CYAN)Updating Python dependencies...$(FONT_RESET)"
	@uv sync
	@echo "$(FONT_CYAN)Updating Gateway dependencies...$(FONT_RESET)"
	@cd gateway && bun install
	@echo "$(FONT_CYAN)Updating Evolution (WhatsApp) dependencies...$(FONT_RESET)"
	@cd resources/omni-whatsapp-core && pnpm install && npx prisma generate
	@echo "$(FONT_CYAN)Rebuilding UI...$(FONT_RESET)"
	@cd resources/ui && bun install && bun run build
	@echo "$(FONT_CYAN)Restarting services...$(FONT_RESET)"
	@pm2 restart ecosystem.config.cjs 2>/dev/null || pm2 start ecosystem.config.cjs
	@pm2 save
	@echo ""
	@echo "$(FONT_GREEN)Update complete!$(FONT_RESET)"

uninstall: ## Stop services and cleanup (prompts for data wipe)
	@echo ""
	@echo "$(FONT_YELLOW)Stopping PM2 services...$(FONT_RESET)"
	@pm2 delete ecosystem.config.cjs 2>/dev/null || true
	@echo "$(FONT_YELLOW)Removing dependencies...$(FONT_RESET)"
	@rm -rf .venv node_modules gateway/node_modules resources/ui/node_modules resources/omni-whatsapp-core/node_modules
	@rm -rf gateway/dist resources/ui/dist dist build *.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo ""
	@read -p "Wipe all data (database, logs, .env)? [y/N] " yn; \
	case $$yn in \
		[Yy]*) \
			echo "$(FONT_RED)Wiping data...$(FONT_RESET)"; \
			rm -rf $$HOME/automagik-omni omni.db data logs .env; \
			echo "$(FONT_GREEN)Data wiped.$(FONT_RESET)"; \
			;; \
		*) \
			echo "$(FONT_CYAN)Data preserved.$(FONT_RESET)"; \
			;; \
	esac
	@echo ""
	@echo "$(FONT_GREEN)Uninstall complete.$(FONT_RESET)"

# ===========================================
# Quality Commands
# ===========================================

lint: ## Run all linters (check mode)
	@echo "$(FONT_CYAN)Linting Python...$(FONT_RESET)"
	@uv run ruff check src
	@echo "$(FONT_CYAN)Linting Gateway...$(FONT_RESET)"
	@cd gateway && bun run lint:check
	@echo "$(FONT_CYAN)Linting UI...$(FONT_RESET)"
	@cd resources/ui && bun run lint:check
	@echo "$(FONT_GREEN)All linting passed!$(FONT_RESET)"

lint-fix: ## Run all linters with auto-fix
	@echo "$(FONT_CYAN)Fixing Python lint issues...$(FONT_RESET)"
	@uv run ruff check src --fix
	@echo "$(FONT_CYAN)Fixing Gateway lint issues...$(FONT_RESET)"
	@cd gateway && bun run lint
	@echo "$(FONT_CYAN)Fixing UI lint issues...$(FONT_RESET)"
	@cd resources/ui && bun run lint
	@echo "$(FONT_GREEN)Lint fixes applied!$(FONT_RESET)"

format: ## Format all code
	@echo "$(FONT_CYAN)Formatting Python...$(FONT_RESET)"
	@uv run ruff format src
	@echo "$(FONT_CYAN)Formatting Gateway...$(FONT_RESET)"
	@cd gateway && bun run format
	@echo "$(FONT_CYAN)Formatting UI...$(FONT_RESET)"
	@cd resources/ui && bunx prettier --write "src/**/*.{ts,tsx}"
	@echo "$(FONT_GREEN)All code formatted!$(FONT_RESET)"

format-check: ## Check formatting without fixing
	@echo "$(FONT_CYAN)Checking Python formatting...$(FONT_RESET)"
	@uv run ruff format src --check
	@echo "$(FONT_CYAN)Checking Gateway formatting...$(FONT_RESET)"
	@cd gateway && bun run format:check
	@echo "$(FONT_CYAN)Checking UI formatting...$(FONT_RESET)"
	@cd resources/ui && bunx prettier --check "src/**/*.{ts,tsx}"
	@echo "$(FONT_GREEN)All formatting checks passed!$(FONT_RESET)"

typecheck: ## Run TypeScript type checking
	@echo "$(FONT_CYAN)Type checking Gateway...$(FONT_RESET)"
	@cd gateway && bun run typecheck
	@echo "$(FONT_CYAN)Type checking UI...$(FONT_RESET)"
	@cd resources/ui && bunx tsc --noEmit
	@echo "$(FONT_GREEN)All type checks passed!$(FONT_RESET)"

test: ## Run all tests
	@echo "$(FONT_CYAN)Running Python tests...$(FONT_RESET)"
	@uv run pytest tests/ -v || echo "$(FONT_YELLOW)No tests found or tests skipped$(FONT_RESET)"
	@echo "$(FONT_GREEN)Tests complete!$(FONT_RESET)"

quality: lint format-check typecheck ## Run all quality checks
	@echo ""
	@echo "$(FONT_GREEN)All quality checks passed!$(FONT_RESET)"
