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

define prompt_user
	@read -p "$(1) [y/N] " -n 1 -r REPLY; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		exit 0; \
	else \
		echo -e "$(FONT_YELLOW)Skipped.$(FONT_RESET)"; \
		exit 1; \
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
	@echo -e "$(FONT_BOLD)Quick Start:$(FONT_RESET)"
	@echo -e "  $(FONT_GREEN)$(FONT_BOLD)setup          $(FONT_RESET) $(FONT_BOLD)Complete setup for fresh deployment (recommended!)$(FONT_RESET)"
	@echo -e "  $(FONT_CYAN)up             $(FONT_RESET) Quick start: install + dev server"
	@echo -e "  $(FONT_GREEN)deploy-service $(FONT_RESET) Deploy as service: install + service + start"
	@echo ""
	@echo -e "$(FONT_BOLD)Development:$(FONT_RESET)"
	@echo -e "  $(FONT_CYAN)install        $(FONT_RESET) Install Omni core deps (WhatsApp/Evolution) with optional Discord prompt"
	@echo -e "  $(FONT_CYAN)install-omni   $(FONT_RESET) Install only Omni core dependencies (Python)"
	@echo -e "  $(FONT_CYAN)install-evolution$(FONT_RESET) Install Evolution API dependencies (Node.js)"
	@echo -e "  $(FONT_CYAN)install-discord $(FONT_RESET) Install optional Discord extras"
	@echo -e "  $(FONT_CYAN)dev            $(FONT_RESET) Start Omni development server with auto-reload"
	@echo -e "  $(FONT_CYAN)dev-all        $(FONT_RESET) Start Omni + Evolution API in development mode"
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
	@echo ""
	@echo -e "$(FONT_BOLD)Evolution API Management:$(FONT_RESET)"
	@echo -e "  $(FONT_GREEN)evo-start      $(FONT_RESET) Start Evolution API server"
	@echo -e "  $(FONT_GREEN)evo-stop       $(FONT_RESET) Stop Evolution API server"
	@echo -e "  $(FONT_GREEN)evo-restart    $(FONT_RESET) Restart Evolution API server"
	@echo -e "  $(FONT_GREEN)evo-status     $(FONT_RESET) Show Evolution API status"
	@echo -e "  $(FONT_GREEN)evo-logs       $(FONT_RESET) Show Evolution API logs"
	@echo -e "  $(FONT_GREEN)evo            $(FONT_RESET) Alias for evo-start"
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
	@echo -e "$(FONT_BOLD)Quality Checks:$(FONT_RESET)"
	@echo -e "  $(FONT_CYAN)check          $(FONT_RESET) Quick check: quality + tests"
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
# 🐘 Evolution API Management
# ===========================================
.PHONY: evo-start evo-stop evo-restart evo-status evo-logs evo

evo-start: ## Start Evolution API server in development mode
	$(call ensure_env_file)
	$(call print_status,Starting Evolution API server in development mode)
	@cd resources/evolution-api && { \
		if command -v pnpm >/dev/null 2>&1; then \
			echo -e "$(FONT_CYAN)$(INFO) Using pnpm to start Evolution API$(FONT_RESET)"; \
			pnpm run dev:server; \
		elif command -v npm >/dev/null 2>&1; then \
			echo -e "$(FONT_CYAN)$(INFO) Using npm to start Evolution API$(FONT_RESET)"; \
			npm run dev:server; \
		else \
			echo -e "$(FONT_RED)$(ERROR) Neither pnpm nor npm found!$(FONT_RESET)"; \
			exit 1; \
		fi; \
	}

evo-stop: ## Stop Evolution API server
	$(call print_status,Stopping Evolution API server)
	@pkill -f "node.*evolution-api" || echo -e "$(FONT_YELLOW)$(WARNING) Evolution API not running$(FONT_RESET)"
	$(call print_success,Evolution API server stopped)

evo-restart: evo-stop evo-start ## Restart Evolution API server

evo-status: ## Show Evolution API server status
	$(call print_status,Checking Evolution API status)
	@if pgrep -f "node.*evolution-api" > /dev/null; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Evolution API is running$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)PIDs: $$(pgrep -f 'node.*evolution-api' | tr '\n' ' ')$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_RED)$(ERROR) Evolution API is not running$(FONT_RESET)"; \
	fi

evo-logs: ## Show Evolution API logs
	$(call print_status,Showing Evolution API logs)
	@if [ -f logs/evolution-combined.log ]; then \
		tail -f logs/evolution-combined.log; \
	elif [ -f resources/evolution-api/logs/app.log ]; then \
		tail -f resources/evolution-api/logs/app.log; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) No Evolution API logs found$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Start Evolution with: make evo-start$(FONT_RESET)"; \
	fi

evo: evo-start ## Quick alias to start Evolution API

# ===========================================
# 🏗️ Development Commands
# ===========================================
.PHONY: install install-omni install-discord install-evolution
install: ## $(ROCKET) Full production installation (inspired by automagik-tools)
	@$(call show_automagik_logo)
	$(call print_status,Starting automagik-omni installation...)
	@echo ""

	@# Phase 1: Prerequisites
	$(call print_status,Phase 1/7: Checking prerequisites...)
	@$(call check_prerequisites)
	@if ! command -v pnpm >/dev/null 2>&1; then \
		$(call print_error,pnpm not found); \
		echo -e "$(FONT_YELLOW)💡 Install pnpm: npm install -g pnpm$(FONT_RESET)"; \
		exit 1; \
	fi
	$(call print_success,Prerequisites verified!)
	@echo ""

	@# Phase 2: Environment
	$(call print_status,Phase 2/7: Setting up environment...)
	@$(call ensure_env_file)
	@# Auto-generate Evolution API key if not exists (Omni owns Evolution)
	@if ! grep -q "EVOLUTION_API_KEY=" .env 2>/dev/null; then \
		GENERATED_KEY=$$(openssl rand -hex 16); \
		echo "EVOLUTION_API_KEY=$$GENERATED_KEY" >> .env; \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Evolution API key generated: $$GENERATED_KEY$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_CYAN)$(INFO) Using existing Evolution API key$(FONT_RESET)"; \
	fi
	$(call print_success,Environment configured!)
	@echo ""

	@# Phase 3: Python dependencies
	$(call print_status,Phase 3/7: Installing Python dependencies...)
	@$(UV) sync
	$(call print_success,Python dependencies installed!)
	@echo ""

	@# Phase 4: Gateway build
	$(call print_status,Phase 4/7: Building Gateway...)
	@cd gateway && pnpm install --silent
	@cd gateway && pnpm run build
	$(call print_success,Gateway built successfully!)
	@echo ""

	@# Phase 5: UI build
	$(call print_status,Phase 5/7: Building UI...)
	@cd resources/ui && pnpm install --silent
	@cd resources/ui && pnpm run build
	$(call print_success,UI built successfully!)
	@echo ""

	@# Phase 6: PM2 setup
	$(call print_status,Phase 6/7: PM2 Process Manager)
	@if command -v pm2 >/dev/null 2>&1; then \
		PM2_VERSION=$$(pm2 --version 2>/dev/null || echo "unknown"); \
		echo -e "$(FONT_GREEN)$(CHECKMARK) PM2 $$PM2_VERSION already installed$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) PM2 not installed$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)PM2 is a process manager for Node.js applications.$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Features: auto-restart, log management, monitoring$(FONT_RESET)"; \
		read -p "Install PM2 globally? [y/N] " yn; \
		case $$yn in [Yy]*) ;; *) exit 0 ;; esac; \
		echo -e "$(FONT_PURPLE)$(HUB) Installing PM2...$(FONT_RESET)"; \
		npm install -g pm2 || { \
			echo -e "$(FONT_RED)$(ERROR) PM2 installation failed$(FONT_RESET)"; \
			echo -e "$(FONT_YELLOW)💡 Try: sudo npm install -g pm2$(FONT_RESET)"; \
			exit 1; \
		}; \
		PM2_VERSION=$$(pm2 --version); \
		echo -e "$(FONT_GREEN)$(CHECKMARK) PM2 $$PM2_VERSION installed!$(FONT_RESET)"; \
		pm2 update 2>/dev/null || true; \
	fi
	@echo ""

	@# Phase 7: Service setup
	$(call print_status,Phase 7/7: Starting Services Automatically...)
	@if command -v pm2 >/dev/null 2>&1; then \
		echo -e "$(FONT_PURPLE)$(HUB) Starting services...$(FONT_RESET)"; \
		pm2 start ecosystem.config.cjs 2>/dev/null || pm2 restart "$(OMNI_PORT)-automagik-omni" 2>/dev/null; \
		pm2 save --force; \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Services started!$(FONT_RESET)"; \
		echo ""; \
		echo -e "$(FONT_PURPLE)$(HUB) Waiting for services to be ready...$(FONT_RESET)"; \
		$(MAKE) wait-for-services 2>/dev/null || echo -e "$(FONT_YELLOW)$(WARNING) Health check failed - services may need more time$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) PM2 not installed - services not started$(FONT_RESET)"; \
	fi
	@echo ""
	@$(call print_success_with_logo,Installation complete! Services are running.)
	@echo ""
	@echo -e "$(FONT_CYAN)🎉 Installation complete! Gateway running on port $(OMNI_PORT):$(FONT_RESET)"
	@echo ""
	@echo -e "   $(FONT_PURPLE)📡 Gateway:$(FONT_RESET)    http://localhost:$(OMNI_PORT)"
	@echo -e "   $(FONT_PURPLE)🌐 Dashboard:$(FONT_RESET)  http://localhost:$(OMNI_PORT)/"
	@echo -e "   $(FONT_PURPLE)🔍 Health:$(FONT_RESET)     http://localhost:$(OMNI_PORT)/health"
	@echo -e "   $(FONT_PURPLE)📚 API Docs:$(FONT_RESET)   http://localhost:$(OMNI_PORT)/docs"
	@echo ""
	@echo -e "$(FONT_CYAN)📋 Available commands:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)make dev$(FONT_RESET)        - Start development mode"
	@echo -e "  $(FONT_PURPLE)make play$(FONT_RESET)       - Run visual E2E tests"
	@echo -e "  $(FONT_PURPLE)make play-quick$(FONT_RESET) - Run quick smoke tests"
	@echo -e "  $(FONT_PURPLE)make stop$(FONT_RESET)       - Stop all services"
	@echo -e "  $(FONT_PURPLE)make test$(FONT_RESET)       - Run Python tests"
	@echo -e "  $(FONT_PURPLE)make test-ui$(FONT_RESET)    - Run UI tests (headless)"
	@echo ""

install-omni: ## Install Omni core dependencies (WhatsApp/Evolution stack)
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Installing Omni core dependencies with uv)
	@if ! $(UV) sync 2>/dev/null; then \
		echo -e "$(FONT_YELLOW)$(WARNING) Installation failed - clearing UV cache and retrying...$(FONT_RESET)"; \
		$(UV) cache clean; \
		$(UV) sync; \
	fi
	$(call print_success,Omni core dependencies installed)

install-discord: ## Install optional Discord extras
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Installing optional Discord dependencies)
	@$(UV) pip install -e '.[discord]'
	$(call print_success,Discord dependencies installed)

install-evolution: ## Install Evolution API dependencies (Node.js)
	$(call print_status,Checking Evolution API submodule)
	@if [ ! -d "resources/evolution-api" ] || [ ! -f "resources/evolution-api/package.json" ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) Evolution API submodule not initialized$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)$(INFO) Initializing Evolution API submodule...$(FONT_RESET)"; \
		if ! git ls-tree HEAD resources/evolution-api | grep -q '^160000'; then \
			echo -e "$(FONT_YELLOW)$(WARNING) Submodule gitlink missing - restoring from repository$(FONT_RESET)"; \
			git checkout c59bddf -- resources/evolution-api 2>/dev/null || true; \
		fi; \
		git submodule sync && git submodule update --init --recursive; \
	fi
	$(call print_status,Installing Evolution API dependencies)
	@cd resources/evolution-api && { \
		if command -v pnpm >/dev/null 2>&1; then \
			echo -e "$(FONT_CYAN)$(INFO) Using pnpm for Evolution API installation$(FONT_RESET)"; \
			pnpm install; \
		elif command -v npm >/dev/null 2>&1; then \
			echo -e "$(FONT_CYAN)$(INFO) Using npm for Evolution API installation$(FONT_RESET)"; \
			npm install; \
		else \
			echo -e "$(FONT_RED)$(ERROR) Neither pnpm nor npm found!$(FONT_RESET)"; \
			echo -e "$(FONT_YELLOW)💡 Install Node.js and npm/pnpm first$(FONT_RESET)"; \
			exit 1; \
		fi; \
	}
	$(call print_status,Generating Prisma client for PGlite)
	@cd resources/evolution-api && DATABASE_PROVIDER=pglite npm run db:generate
	$(call print_status,Creating Evolution API PGlite database directory)
	@mkdir -p "$$HOME/data/evolution-pglite"
	$(call print_info,PGlite database will be created automatically on first run at $$HOME/data/evolution-pglite)
	$(call print_success,Evolution API dependencies installed)

.PHONY: setup
setup: ## Complete setup for fresh deployment (install all deps + migrations + PM2)
	@echo ""
	@echo -e "$(FONT_PURPLE)$(FONT_BOLD)╔═══════════════════════════════════════════════════════════════╗$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)$(FONT_BOLD)║  $(ROCKET) Automagik Omni - Complete Environment Setup        ║$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)$(FONT_BOLD)╚═══════════════════════════════════════════════════════════════╝$(FONT_RESET)"
	@echo ""
	$(call check_prerequisites)
	$(call print_info,This will set up everything needed for clean PM2 startup)
	@echo ""
	@echo -e "$(FONT_CYAN)Steps to be performed:$(FONT_RESET)"
	@echo -e "  1. Stop and clean existing PM2 processes"
	@echo -e "  2. Install Omni Python dependencies (uv sync)"
	@echo -e "  3. Install Evolution API (Node.js submodule)"
	@echo -e "  4. Optionally install Discord support"
	@echo -e "  5. Create/verify .env configuration"
	@echo -e "  6. Run database migrations"
	@echo -e "  7. Start PM2 services"
	@echo ""
	@read -r -p "Continue with setup? [Y/n] " choice; \
	if [ "$$choice" = "n" ] || [ "$$choice" = "N" ]; then \
		echo "$(FONT_YELLOW)Setup cancelled$(FONT_RESET)"; \
		exit 0; \
	fi
	@echo ""
	$(call print_status,Phase 1: Cleaning existing PM2 processes)
	@if command -v pm2 >/dev/null 2>&1; then \
		pm2 stop all 2>/dev/null || true; \
		pm2 delete all 2>/dev/null || true; \
		echo -e "$(FONT_GREEN)$(CHECKMARK) PM2 processes cleaned$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) PM2 not installed - will skip service management$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)$(INFO) Install PM2 with: npm install -g pm2$(FONT_RESET)"; \
	fi
	@echo ""
	$(call print_status,Phase 2: Installing Omni core dependencies)
	@$(MAKE) install-omni
	@echo ""
	$(call print_status,Phase 3: Installing Evolution API)
	@$(MAKE) install-evolution
	@echo ""
	$(call print_status,Phase 4: Discord support installation)
	@read -r -p "Install optional Discord support? [y/N] " discord_choice; \
	if [ "$$discord_choice" = "y" ] || [ "$$discord_choice" = "Y" ]; then \
		$(MAKE) install-discord; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) Skipping Discord - Discord bot will not start$(FONT_RESET)"; \
	fi
	@echo ""
	$(call print_status,Phase 5: Verifying environment configuration)
	@$(call ensure_env_file)
	@if [ ! -f .env ]; then \
		echo -e "$(FONT_RED)$(ERROR) .env file missing!$(FONT_RESET)"; \
		exit 1; \
	fi
	@echo -e "$(FONT_CYAN)$(INFO) Checking required environment variables...$(FONT_RESET)"
	@if ! grep -q "EVOLUTION_API_KEY" .env 2>/dev/null || [ -z "$$(grep EVOLUTION_API_KEY .env | cut -d= -f2)" ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) EVOLUTION_API_KEY not set in .env$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)$(INFO) You may need to configure Evolution API credentials$(FONT_RESET)"; \
	fi
	@if ! grep -q "AUTOMAGIK_OMNI_API_KEY" .env 2>/dev/null || [ -z "$$(grep AUTOMAGIK_OMNI_API_KEY .env | cut -d= -f2)" ]; then \
		echo -e "$(FONT_YELLOW)$(WARNING) AUTOMAGIK_OMNI_API_KEY not set in .env$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)$(INFO) You may need to set an API key for security$(FONT_RESET)"; \
	fi
	$(call print_success,Environment configuration verified)
	@echo ""
	$(call print_status,Phase 6: Running database migrations)
	@$(UV) run alembic upgrade head
	$(call print_success,Database migrations completed)
	@echo ""
	@if command -v pm2 >/dev/null 2>&1; then \
		echo -e "$(FONT_PURPLE)$(HUB) Phase 7: Starting PM2 services$(FONT_RESET)"; \
		pm2 start ecosystem.config.js; \
		sleep 3; \
		echo ""; \
		echo -e "$(FONT_GREEN)$(CHECKMARK) PM2 services started$(FONT_RESET)"; \
		echo ""; \
		echo -e "$(FONT_CYAN)$(INFO) Checking service health...$(FONT_RESET)"; \
		pm2 list; \
		echo ""; \
		echo -e "$(FONT_GREEN)$(FONT_BOLD)╔═══════════════════════════════════════════════════════════════╗$(FONT_RESET)"; \
		echo -e "$(FONT_GREEN)$(FONT_BOLD)║  $(CHECKMARK) Setup Complete! Services are running               ║$(FONT_RESET)"; \
		echo -e "$(FONT_GREEN)$(FONT_BOLD)╚═══════════════════════════════════════════════════════════════╝$(FONT_RESET)"; \
		echo ""; \
		echo -e "$(FONT_BOLD)Next steps:$(FONT_RESET)"; \
		echo -e "  $(FONT_CYAN)• View logs:$(FONT_RESET)       pm2 logs"; \
		echo -e "  $(FONT_CYAN)• Check status:$(FONT_RESET)    pm2 list"; \
		echo -e "  $(FONT_CYAN)• Stop services:$(FONT_RESET)   pm2 stop all"; \
		echo -e "  $(FONT_CYAN)• API Health:$(FONT_RESET)      curl http://localhost:8882/health"; \
		echo ""; \
	else \
		echo ""; \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Setup complete - PM2 not installed$(FONT_RESET)"; \
		echo ""; \
		echo -e "$(FONT_YELLOW)$(WARNING) PM2 not found - services not started$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)To install PM2: npm install -g pm2$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Then run: pm2 start ecosystem.config.js$(FONT_RESET)"; \
		echo ""; \
	fi

.PHONY: dev dev-all
dev: ## Start Omni development server with auto-reload
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Starting Omni development server with auto-reload)
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs) && \
		$(UV) run automagik-omni start --host $${AUTOMAGIK_OMNI_API_HOST:-0.0.0.0} --port $${AUTOMAGIK_OMNI_API_PORT:-8882} --reload; \
	else \
		$(UV) run automagik-omni start --host $(AUTOMAGIK_OMNI_API_HOST) --port $(AUTOMAGIK_OMNI_API_PORT) --reload; \
	fi

dev-all: ## Start both Omni and Evolution API in development mode (parallel)
	$(call check_prerequisites)
	$(call ensure_env_file)
	$(call print_status,Starting Omni + Evolution API in development mode)
	@echo -e "$(FONT_CYAN)$(INFO) Starting Evolution API in background...$(FONT_RESET)"
	@cd resources/evolution-api && { \
		if command -v pnpm >/dev/null 2>&1; then \
			pnpm run dev:server > ../../logs/evolution-dev.log 2>&1 & \
		elif command -v npm >/dev/null 2>&1; then \
			npm run dev:server > ../../logs/evolution-dev.log 2>&1 & \
		else \
			echo -e "$(FONT_RED)$(ERROR) Neither pnpm nor npm found!$(FONT_RESET)"; \
			exit 1; \
		fi; \
	}
	@sleep 2
	@echo -e "$(FONT_GREEN)$(CHECKMARK) Evolution API started (logs: logs/evolution-dev.log)$(FONT_RESET)"
	@echo -e "$(FONT_CYAN)$(INFO) Starting Omni API server...$(FONT_RESET)"
	@if [ -f .env ]; then \
		export $$(cat .env | grep -v '^#' | xargs) && \
		$(UV) run automagik-omni start --host $${AUTOMAGIK_OMNI_API_HOST:-0.0.0.0} --port $${AUTOMAGIK_OMNI_API_PORT:-8882} --reload; \
	else \
		$(UV) run automagik-omni start --host $(AUTOMAGIK_OMNI_API_HOST) --port $(AUTOMAGIK_OMNI_API_PORT) --reload; \
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

.PHONY: play play-full play-quick test-ui test-ui-quick wait-for-services
play: play-full ## Run visual Playwright E2E tests (human-watchable)

play-full: ## Run comprehensive Playwright tests in headed mode
	$(call print_status,Running comprehensive Playwright tests (headed mode))
	@cd resources/ui && npm run test:e2e:ui
	$(call print_success,Playwright tests completed)

play-quick: ## Run quick smoke tests in headed mode
	$(call print_status,Running quick smoke tests (headed mode))
	@cd resources/ui && npm run test:quick:ui
	$(call print_success,Quick smoke tests completed)

test-ui: ## Run UI tests in headless mode (for CI)
	$(call print_status,Running UI tests (headless))
	@cd resources/ui && npm run test:e2e
	$(call print_success,UI tests completed)

test-ui-quick: ## Run quick UI tests in headless mode
	$(call print_status,Running quick UI tests (headless))
	@cd resources/ui && npm run test:quick
	$(call print_success,Quick UI tests completed)

wait-for-services: ## Wait for services to be healthy
	$(call print_status,Checking service health...)
	@echo "Waiting for Gateway (port $(OMNI_PORT))..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -s http://localhost:$(OMNI_PORT)/health > /dev/null 2>&1; then \
			echo -e "$(FONT_GREEN)$(CHECKMARK) Gateway ready$(FONT_RESET)"; \
			break; \
		fi; \
		echo "⏳ Attempt $$i/10..."; \
		sleep 2; \
	done
	$(call print_success,All services healthy!)

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
format: ## Format code with ruff
	$(call check_prerequisites)
	$(call print_status,Formatting code with ruff)
	@$(UV) run ruff format src/ tests/
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

# ===========================================
# 🎨 Frontend / UI Targets
# ===========================================

UI_DIR := resources/ui
UI_PORT ?= 9882
UI_HOST ?= 0.0.0.0

.PHONY: ui-install ui-dev ui-build ui-preview frontend ui-clean

ui-install: ## Install UI dependencies
	$(call print_status,Installing UI dependencies...)
	@cd $(UI_DIR) && pnpm install
	$(call print_success,UI dependencies installed)

ui-dev: ## Run UI development server (standalone)
	$(call print_status,Starting UI dev server...)
	@cd $(UI_DIR) && UI_HOST=$(UI_HOST) UI_PORT=$(UI_PORT) VITE_API_URL=http://$(AUTOMAGIK_OMNI_API_HOST):$(AUTOMAGIK_OMNI_API_PORT) pnpm run dev

ui-build: ## Build UI for production
	$(call print_status,Building UI for production...)
	@cd $(UI_DIR) && pnpm run build
	$(call print_success,UI built successfully → $(UI_DIR)/dist/)

ui-preview: ui-build ## Preview production build
	$(call print_status,Starting UI preview server...)
	@cd $(UI_DIR) && pnpm run preview

ui-clean: ## Clean UI build artifacts
	$(call print_status,Cleaning UI build artifacts...)
	@rm -rf $(UI_DIR)/dist $(UI_DIR)/node_modules
	$(call print_success,UI artifacts cleaned)

frontend: ui-dev ## Alias for ui-dev (run frontend standalone)

frontend-build: ui-build ## Build frontend for production

frontend-prod: ui-preview ## Run frontend production preview server

# ===========================================
# 🚀 Integrated Setup (API + UI)
# ===========================================

.PHONY: install-all dev-pm2

install-all: install ui-install ## Install both API and UI dependencies
	$(call print_success_with_logo,All dependencies installed (API + UI))

dev-pm2: ## Start both API and UI in PM2
	$(call print_status,Starting Omni API + UI services via PM2...)
	@pm2 start ecosystem.config.js
	@pm2 save
	$(call print_success,Services started!)
	$(call print_info,API: http://$(AUTOMAGIK_OMNI_API_HOST):$(AUTOMAGIK_OMNI_API_PORT))
	$(call print_info,UI:  http://$(UI_HOST):$(UI_PORT))
	$(call print_info,Monitor: pm2 monit)

# ===========================================
# 🏭 Production Deployment (PM2 Gateway Mode)
# ===========================================
# Only the Gateway port is user-configurable
# Internal service ports (Python, Evolution, Vite) are auto-managed
OMNI_PORT ?= 8882

.PHONY: prod prod-setup prod-start prod-stop prod-restart prod-status prod-logs prod-build

prod: ## 🏭 Full production setup and start (recommended for fresh deployment)
	@echo ""
	@echo -e "$(FONT_PURPLE)$(FONT_BOLD)╔═══════════════════════════════════════════════════════════════╗$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)$(FONT_BOLD)║  $(ROCKET) Automagik Omni - Production Deployment               ║$(FONT_RESET)"
	@echo -e "$(FONT_PURPLE)$(FONT_BOLD)╚═══════════════════════════════════════════════════════════════╝$(FONT_RESET)"
	@echo ""
	@echo -e "$(FONT_CYAN)This will set up Omni Hub for production with:$(FONT_RESET)"
	@echo -e "  • Gateway on port $(OMNI_PORT) (single entry point)"
	@echo -e "  • Python API (auto-managed port, internal)"
	@echo -e "  • Evolution API (auto-managed port, internal)"
	@echo -e "  • Built UI served by Gateway"
	@echo ""
	@read -r -p "Continue with production setup? [Y/n] " choice; \
	if [ "$$choice" = "n" ] || [ "$$choice" = "N" ]; then \
		echo "$(FONT_YELLOW)Setup cancelled$(FONT_RESET)"; \
		exit 0; \
	fi
	@$(MAKE) prod-setup
	@$(MAKE) prod-start
	@echo ""
	@echo -e "$(FONT_GREEN)$(FONT_BOLD)╔═══════════════════════════════════════════════════════════════╗$(FONT_RESET)"
	@echo -e "$(FONT_GREEN)$(FONT_BOLD)║  $(CHECKMARK) Production Deployment Complete!                       ║$(FONT_RESET)"
	@echo -e "$(FONT_GREEN)$(FONT_BOLD)╚═══════════════════════════════════════════════════════════════╝$(FONT_RESET)"
	@echo ""
	@echo -e "$(FONT_BOLD)Services:$(FONT_RESET)"
	@echo -e "  $(FONT_GREEN)•$(FONT_RESET) Gateway:     http://0.0.0.0:$(OMNI_PORT)"
	@echo -e "  $(FONT_GREEN)•$(FONT_RESET) Dashboard:   http://0.0.0.0:$(OMNI_PORT)/dashboard"
	@echo -e "  $(FONT_GREEN)•$(FONT_RESET) API Health:  http://0.0.0.0:$(OMNI_PORT)/health"
	@echo ""
	@echo -e "$(FONT_BOLD)PM2 Commands:$(FONT_RESET)"
	@echo -e "  $(FONT_CYAN)make prod-status$(FONT_RESET)   - Check service status"
	@echo -e "  $(FONT_CYAN)make prod-logs$(FONT_RESET)     - View logs"
	@echo -e "  $(FONT_CYAN)make prod-restart$(FONT_RESET)  - Restart services"
	@echo -e "  $(FONT_CYAN)make prod-stop$(FONT_RESET)     - Stop services"
	@echo ""

prod-setup: ## 🔧 Setup production environment (install deps, build, configure)
	$(call print_status,Phase 1: Checking prerequisites)
	$(call check_prerequisites)
	@if ! command -v pm2 >/dev/null 2>&1; then \
		echo -e "$(FONT_RED)$(ERROR) PM2 not installed$(FONT_RESET)"; \
		echo -e "$(FONT_CYAN)Install with: npm install -g pm2$(FONT_RESET)"; \
		exit 1; \
	fi
	@if ! command -v node >/dev/null 2>&1; then \
		echo -e "$(FONT_RED)$(ERROR) Node.js not installed$(FONT_RESET)"; \
		exit 1; \
	fi
	$(call print_success,Prerequisites verified)
	@echo ""
	$(call print_status,Phase 2: Creating environment file)
	@if [ ! -f ".env" ]; then \
		if [ -f ".env.example" ]; then \
			cp .env.example .env; \
			echo -e "$(FONT_GREEN)$(CHECKMARK) Created .env from .env.example$(FONT_RESET)"; \
		else \
			echo "OMNI_PORT=$(OMNI_PORT)" > .env; \
			echo "ENVIRONMENT=production" >> .env; \
			echo "LOG_LEVEL=INFO" >> .env; \
			echo -e "$(FONT_GREEN)$(CHECKMARK) Created minimal .env file$(FONT_RESET)"; \
		fi; \
		echo -e "$(FONT_YELLOW)$(WARNING) Please review and configure .env before starting$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_GREEN)$(CHECKMARK) .env file exists$(FONT_RESET)"; \
	fi
	@echo ""
	$(call print_status,Phase 3: Installing Python dependencies)
	@$(MAKE) install-omni
	@echo ""
	$(call print_status,Phase 4: Running database migrations)
	@$(UV) run alembic upgrade head
	$(call print_success,Database migrations completed)
	@echo ""
	$(call print_status,Phase 5: Installing Evolution API)
	@$(MAKE) install-evolution
	@echo ""
	$(call print_status,Phase 6: Installing Gateway dependencies)
	@cd gateway && pnpm install
	$(call print_success,Gateway dependencies installed)
	@echo ""
	$(call print_status,Phase 7: Building Gateway)
	@cd gateway && pnpm run build
	$(call print_success,Gateway built)
	@echo ""
	$(call print_status,Phase 8: Installing UI dependencies)
	@cd resources/ui && pnpm install
	$(call print_success,UI dependencies installed)
	@echo ""
	$(call print_status,Phase 9: Building UI for production)
	@cd resources/ui && pnpm run build
	$(call print_success,UI built for production)
	@echo ""
	$(call print_status,Phase 10: Setting up PM2 startup)
	@pm2 startup 2>/dev/null || echo -e "$(FONT_YELLOW)$(WARNING) Run 'pm2 startup' manually if you want auto-restart on boot$(FONT_RESET)"
	$(call print_success,Production setup completed!)

prod-start: ## ▶️  Start production services with PM2
	$(call print_status,Starting production services...)
	@# Stop any existing processes first
	@pm2 delete "$(OMNI_PORT): Omni-Gateway" 2>/dev/null || true
	@pm2 delete "Omni-Evolution-API" 2>/dev/null || true
	@# Start Evolution API (port auto-managed internally)
	$(call print_info,Starting Evolution API...)
	@cd resources/evolution-api && pm2 start npm --name "Omni-Evolution-API" \
		--cwd "$(PROJECT_ROOT)/resources/evolution-api" \
		--time \
		--log-date-format "YYYY-MM-DD HH:mm:ss" \
		-- run start
	@sleep 3
	@# Start Gateway (manages Python API and proxies to Evolution)
	$(call print_info,Starting Gateway on port $(OMNI_PORT)...)
	@pm2 start gateway/dist/index.js --name "$(OMNI_PORT): Omni-Gateway" \
		--cwd "$(PROJECT_ROOT)" \
		--time \
		--log-date-format "YYYY-MM-DD HH:mm:ss" \
		--node-args="--max-old-space-size=512" \
		--env production
	@sleep 3
	@# Save PM2 configuration
	@pm2 save
	$(call print_success,Production services started!)
	@pm2 list

prod-stop: ## ⏹️  Stop production services
	$(call print_status,Stopping production services...)
	@pm2 stop "$(OMNI_PORT): Omni-Gateway" 2>/dev/null || true
	@pm2 stop "Omni-Evolution-API" 2>/dev/null || true
	@pm2 save
	$(call print_success,Production services stopped)

prod-restart: ## 🔄 Restart production services
	$(call print_status,Restarting production services...)
	@pm2 restart "Omni-Evolution-API" 2>/dev/null || $(MAKE) prod-start
	@pm2 restart "$(OMNI_PORT): Omni-Gateway" 2>/dev/null || $(MAKE) prod-start
	@pm2 save
	$(call print_success,Production services restarted)
	@pm2 list

prod-status: ## 📊 Show production service status
	$(call print_status,Production service status)
	@pm2 list
	@echo ""
	@echo -e "$(FONT_CYAN)Health Check:$(FONT_RESET)"
	@curl -s http://localhost:$(OMNI_PORT)/health 2>/dev/null | python3 -c "import sys,json; h=json.load(sys.stdin); print(f'  Gateway: {h[\"services\"][\"gateway\"][\"status\"]}'); print(f'  Python:  {h[\"services\"][\"python\"][\"status\"]}'); print(f'  Evolution: {h[\"services\"][\"evolution\"][\"status\"]}')" 2>/dev/null || echo "  $(FONT_YELLOW)Gateway not responding$(FONT_RESET)"

prod-logs: ## 📜 Show production logs
	$(call print_status,Production logs - Press Ctrl+C to exit)
	@pm2 logs --lines 50

prod-build: ## 🔨 Rebuild Gateway and UI (for updates)
	$(call print_status,Rebuilding Gateway...)
	@cd gateway && pnpm run build
	$(call print_success,Gateway rebuilt)
	$(call print_status,Rebuilding UI...)
	@cd resources/ui && pnpm run build
	$(call print_success,UI rebuilt)
	$(call print_info,Run 'make prod-restart' to apply changes)

# ===========================================
# 🏥 Health Checks
# ===========================================
.PHONY: health
health: ## 🏥 Health check for all services
	@echo ""
	$(call print_status,Running health checks...)
	@echo ""
	@echo "🌐 Gateway Health:"
	@if curl -s http://localhost:8882/health >/dev/null 2>&1; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Gateway healthy (http://localhost:8882)$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_RED)$(ERROR) Gateway unhealthy or not running$(FONT_RESET)"; \
	fi
	@echo ""
	@echo "🐍 Python API Health:"
	@if curl -s http://localhost:8000/health >/dev/null 2>&1; then \
		echo -e "$(FONT_GREEN)$(CHECKMARK) Python API healthy (http://localhost:8000)$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) Python API health check failed (may use different port or endpoint)$(FONT_RESET)"; \
	fi
	@echo ""
	@if command -v pm2 >/dev/null 2>&1; then \
		echo -e "$(FONT_PURPLE)$(HUB) PM2 Status:$(FONT_RESET)"; \
		pm2 status 2>/dev/null || echo -e "$(FONT_YELLOW)$(WARNING) PM2 not running$(FONT_RESET)"; \
	else \
		echo -e "$(FONT_YELLOW)$(WARNING) PM2 not installed$(FONT_RESET)"; \
	fi
	@echo ""

# ===========================================
# 🚀 Installation & Updates
# ===========================================
.PHONY: update
update: ## 🔄 Update installation (git pull + deps + rebuild + restart + health check)
	$(call print_status,Updating automagik-omni...)
	@echo ""

	@# Step 1: Git pull
	$(call print_status,Pulling latest changes from git...)
	@git pull || { \
		$(call print_error,Git pull failed); \
		exit 1; \
	}
	$(call print_success,Latest changes pulled!)
	@echo ""

	@# Step 2: Update dependencies and rebuild
	$(call print_status,Updating dependencies and rebuilding...)
	@echo ""
	$(call print_status,Installing Python dependencies...)
	@$(UV) sync
	$(call print_success,Python dependencies updated!)
	@echo ""
	$(call print_status,Rebuilding Gateway...)
	@cd gateway && pnpm install
	@cd gateway && pnpm run build
	$(call print_success,Gateway rebuilt!)
	@echo ""
	$(call print_status,Rebuilding UI...)
	@cd resources/ui && pnpm install
	@cd resources/ui && pnpm run build
	$(call print_success,UI rebuilt!)
	@echo ""

	@# Step 3: Restart services
	$(call print_status,Restarting services...)
	@# Restart PM2 gateway
	@if command -v pm2 >/dev/null 2>&1 && pm2 show "$(OMNI_PORT)-automagik-omni" >/dev/null 2>&1; then \
		pm2 restart "$(OMNI_PORT)-automagik-omni"; \
		$(call print_success,PM2 gateway restarted); \
	fi
	@# Restart Python API (systemd)
	@if command -v systemctl >/dev/null 2>&1; then \
		echo -e "$(FONT_CYAN)$(INFO) Attempting to restart Python API (requires sudo)...$(FONT_RESET)"; \
		sudo systemctl restart omni-python 2>/dev/null && $(call print_success,Python API restarted) || \
		$(call print_warning,Could not restart Python API via systemd (may not be installed as service)); \
	fi
	@echo ""

	@# Step 4: Health check
	$(call print_status,Running health checks...)
	@sleep 2
	@$(MAKE) health || { \
		$(call print_warning,Health check failed - service may need more time to start); \
	}

	@# Success summary
	@echo ""
	@$(call print_success_with_logo,Update completed successfully!)
	@echo -e "$(FONT_CYAN)💡 Useful commands:$(FONT_RESET)"
	@echo -e "  $(FONT_PURPLE)make health$(FONT_RESET)        # Run health check again"
	@echo -e "  $(FONT_PURPLE)make prod-status$(FONT_RESET)   # Check PM2 status"
	@echo -e "  $(FONT_PURPLE)make prod-logs$(FONT_RESET)     # View recent logs"
	@echo ""
