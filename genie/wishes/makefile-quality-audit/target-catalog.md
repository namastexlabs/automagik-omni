# Makefile Target Catalog (Initial Classification)

## Help & Overview
- help — prints categorized command list with emojis
- info — prints environment/tooling versions

## Environment & Development Setup
- install — uv dependency sync w/ env bootstrap
- dev — run FastAPI w/ uvicorn & reload
- up — convenience: install + dev

## Testing & Coverage
- test — pytest default backend
- test-coverage — pytest w/ HTML + term coverage
- test-coverage-summary — pytest coverage summary only
- test-sqlite — pytest forcing SQLite params
- test-postgres — pytest w/ Postgres (env or script)
- test-postgres-setup — start dockerized Postgres helper script
- test-postgres-teardown — stop/remove Postgres helper
- check — composite: quality + test

## Quality & Formatting
- lint — ruff check src/tests
- lint-fix — ruff check --fix
- format — black src/tests
- typecheck — mypy src
- quality — alias: lint + typecheck (no format)

## PM2 Local Service Lifecycle
- setup-pm2 — ensures config & pm2 presence
- start-local — start pm2 ecosystem
- stop-local — stop pm2 proc
- restart-local — restart pm2 proc
- status-local — pm2 show automagik-omni
- logs-local — pm2 logs (bounded lines)
- logs-follow-local — pm2 logs tail
- uninstall-service — stop-local + pm2 delete/save

## Service Aliases (Delegating to Local PM2 Targets)
- install-service — make start-local
- start-service — make start-local
- stop-service — make stop-local
- restart-service — make restart-local
- service-status — make status-local
- logs — make logs-local
- logs-follow — make logs-follow-local
- deploy-service — install + start-local (with logo)

## Discord Bot Management
- discord-start — uv CLI to start instance
- discord-stop — uv CLI to stop instance
- discord-restart — uv CLI to restart instance
- discord-status — uv CLI status (single/all)
- discord-logs — pm2 logs for discord process
- discord-list — uv CLI list

## Database & CLI Utilities
- db-init — python snippet ensures default instance
- cli-instances — instance_cli list
- cli-create — instance_cli create (interactive)
- validate — scripts/validate_multitenancy.py

## Build & Release
- clean-build — remove build/dist artifacts
- build — uv build (depends clean-build)
- check-dist — twine check dist/*
- check-release — git status/branch/upstream gate (interactive)
- publish-test — build + check-dist + twine upload testpypi
- publish — push + tag + gh release
- release — quality + test + build (w/ prompts)
- clean — repo cleanup (pycache, coverage, dist, etc.)

## Version Management
- version — prints pyproject version (missing .PHONY)
- version-bump — scripts/bump-version.py with TYPE arg
- bump-patch — increments patch + commits
- bump-minor — increments minor + commits
- bump-major — increments major + commits
- bump-dev — add pre suffix/advance pre counter
- publish-dev — build/check-dist + twine upload pre release
- finalize-version — drop pre suffix

## Observations To Verify Later
- Some release/version targets rely on git clean tree (commits) and network tokens.
- Discord & PM2 targets assume pm2 installed and ecosystem.config.js present.
- Several aliases (install-service/start-service) may be redundant after cleanup.
