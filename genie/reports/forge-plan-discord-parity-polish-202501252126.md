# Forge Execution Plan: Discord Parity Polish

**Wish:** Discord Parity Polish
**Source:** `/genie/wishes/discord-parity-polish-wish.md`
**Generated:** 2025-01-25 21:26 UTC
**Status:** APPROVED

## Executive Summary
Address PR review feedback to achieve 100/100 score through targeted fixes:
- Remove accidental test file
- Enhance migration with server defaults
- Add instance-scoped uniqueness for multi-tenancy
- Implement retry logic for trace persistence
- Improve Discord bot error handling

## Planning

### Proposed Task Groups

#### Group 1: Quick Cleanup
**Agent:** automagik-omni-coder
**Branch:** fix/discord-parity-cleanup
**Scope:**
- Remove `test.md` file
- Verify `.gitignore` properly excludes `.mcp.json`

**Success Criteria:**
- `test.md` no longer exists in repository
- `.mcp.json` confirmed in `.gitignore`

**Dependencies:** None

---

#### Group 2: Migration Enhancements
**Agent:** automagik-omni-coder
**Branch:** fix/migration-server-defaults
**Scope:**
- Update existing migration `7f3a2b1c9a01` with server-default timestamps
- Create new migration for instance-scoped uniqueness constraint
- Update `UserExternalId` model to reflect new constraint

**Success Criteria:**
- Migration applies/rollbacks cleanly
- Instance-scoped uniqueness enforced at DB level

**Dependencies:** None (can run parallel to Group 1)

---

#### Group 3: Service Robustness
**Agent:** automagik-omni-coder
**Branch:** fix/service-error-handling
**Scope:**
- Add retry decorator to `trace_service.py` operations
- Enhance Discord bot manager error handling
- Implement fallback logic for identity resolution failures

**Success Criteria:**
- Transient DB failures handled with exponential backoff
- Discord flow continues even if identity linking fails
- All existing tests remain green

**Dependencies:** Group 2 (for model changes)

---

#### Group 4: Validation & PR Update
**Agent:** automagik-omni-qa-tester
**Branch:** test/discord-parity-validation-final
**Scope:**
- Run full Discord parity test suite
- Verify all fixes work as expected
- Document validation results
- Prepare final PR update

**Success Criteria:**
- All Discord tests green
- Manual smoke tests pass
- PR achieves 100/100 review score

**Dependencies:** Groups 1, 2, 3

## Approval

**Status:** APPROVED by user
**Time:** 2025-01-25 21:27 UTC
**Method:** Direct approval via "/forge approve and forge the tasks"

## Execution

### Created Forge Tasks

#### Group 1: Quick Cleanup
- **Task ID:** 9722b221-8e24-4eb5-80d8-82212d335f7e
- **Branch:** fix/discord-parity-cleanup
- **Agent:** automagik-omni-coder
- **Title:** fix: remove test.md and verify gitignore

#### Group 2: Migration Enhancements
- **Task ID:** eb26738c-57e7-4ebf-9157-d929397724b6
- **Branch:** fix/migration-server-defaults
- **Agent:** automagik-omni-coder
- **Title:** fix: migration server defaults and instance uniqueness

#### Group 3: Service Robustness
- **Task ID:** 20d1bf40-16b0-4cd9-a403-67765cf036c4
- **Branch:** fix/service-error-handling
- **Agent:** automagik-omni-coder
- **Title:** fix: service retry logic and error handling
- **Note:** Depends on Group 2 completion

#### Group 4: Validation & PR Update
- **Task ID:** e9a68b1c-fc92-4ec1-a20d-e6b034cb2eb9
- **Branch:** test/discord-parity-validation-final
- **Agent:** automagik-omni-qa-tester
- **Title:** test: discord parity final validation
- **Note:** Depends on Groups 1, 2, 3 completion

### Execution Notes
- Groups 1 and 2 can be executed in parallel
- Group 3 should start after Group 2 completes (model dependencies)
- Group 4 runs after all implementation groups finish
- Each agent should reference this plan when creating their Death Testament