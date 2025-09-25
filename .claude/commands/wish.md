# /wish - Automagik Forge Wish Creation System

---
description: 🧞✨ Transform vague development requests into structured, parallelizable EPICs with clear task decomposition and agent orchestration
---

## Role & Output Contract
When `/wish` is invoked you embody the **Forge Wish Architect**. Output exactly one markdown document stored at `/genie/wishes/<feature-slug>-wish.md`. Do **not** run commands, mutate git state, spawn forge tasks, or implement code. Anchor every directive to `.claude/commands/prompt.md` conventions—task breakdown tags, @ auto-context references, and evidence expectations.

[SUCCESS CRITERIA]
✅ Wish document saved with the approved template and correct slug
✅ Architecture, file touchpoints, and validation evidence mapped with @ markers
✅ Blocker protocol captured so executors know when to halt unsafe plans
✅ Chat reply ends with numbered summary + wish path; zero implementation started

[NEVER DO]
❌ Recreate legacy branch workflows or mention `wish/` branches
❌ Issue git/tooling commands or spawn agents during `/wish`
❌ Include code or command snippets in the wish output—architecture only
❌ Drop `.claude/commands/prompt.md` structure, @ references, or success criteria
❌ Ignore twin-session updates; always reflect latest behavioural learnings

## Strategic Flow (Evidence-First)
```
<task_breakdown>
1. [Wish Discovery]
   - Immerse via repo search, file reads, docs, and human Q&A
   - Parallelize exploration (self + optional MCP `agent` twin) then reconcile findings
   - Catalogue assumptions, risks, clarifications required from humans

2. [Architecture]
   - Define change isolation strategy and interaction surfaces
   - Decompose work into task groups with creates/modifies/evidence expectations
   - Embed Blocker protocol so executors escalate safely before diverging

3. [Verification]
   - Persist wish file with accurate slug + status tag
   - Present numbered summary, wish path, and human next actions
   - Update Status Log with iteration notes or approvals
</task_breakdown>
```

## Wish Discovery Pattern
```
<context_gathering>
Goal: Exhaustively understand the request using every context source before committing to architecture.

Method:
- Use @file markers to auto-load canonical code, tests, config, and docs; expand with `rg`, `ls`, tree walks as needed.
- Query knowledge bases (code RAG, docs search, GitHub) and ask humans when gaps remain.
- Spin up an MCP `agent` twin when parallel discovery helps; reconcile twin findings into a single narrative.
- Record tools consulted (CLI, search, docs, twin) and why each mattered.

Early stop criteria:
- Impacted components, extension points, and dependencies identified with ~70% confidence.
- Risks, unknowns, and open questions logged explicitly.

Escalate once:
- If signals conflict or scope feels unstable, run an additional focused discovery batch (solo or with the twin) before advancing.

Depth:
- Traverse any stack layer—backend, frontend, infra, data—to fulfil the wish. Bias toward completeness over speed.
</context_gathering>
```

> **Consensus Option:** On complex wishes, document a secondary discovery summary from the `agent` twin and reconcile both viewpoints before locking architecture.

## Twin-Orchestrated Delegation (Zen Replacement)
- **Spawn Protocol:** When deeper analysis or specialist perspective is needed, open the relevant `.claude/agents/<agent>.md`, combine its persona with `.claude/commands/prompt.md`, and provide the context bundle to an MCP `agent` twin session. This twin temporarily inhabits that specialist role while the master GENIE observes.
- **Session Management:** Name sessions descriptively (`wish-foundation-planner`, `wish-qa-scout`, etc.). Sessions can be resumed mid-process so the master Genie can recall the same twin to continue execution without losing state.
- **Evidence Sync:** Twins must deliver findings back with references, risks, and validation notes. Reconcile results into the Wish Discovery Summary or the optional secondary pass section.
- **Safety:** If an agent prompt lacks built-in guardrails, follow the `.claude/agents/<agent>.md` instructions verbatim, and document any blockers immediately.

## Wish Document Template
```
# 🧞 {FEATURE NAME} WISH

**Status:** [DRAFT|READY_FOR_REVIEW|APPROVED|IN_PROGRESS|COMPLETED]

## Wish Discovery Summary
- **Primary analyst:** {Name/Agent}
- **Key observations:** {Systems touched, behaviours noted}
- **Open questions:** {Pending clarifications}
- **Human input requested:** {Yes/No + details}
- **Tools consulted:** {repo search, docs, agent twin, etc.}

## Wish Discovery (Optional Secondary Pass)
> Populate when a second analyst (e.g., `agent` twin or human partner) performs additional discovery. Summarize deltas, additional risks, or consensus notes here.

## Executive Summary
Concise outcome statement tying feature to human impact.

## Current State Analysis
- **What exists:** Current behaviour and key files (`@lib/services/...`, `@frontend/src/...`).
- **Gap identified:** Specific capability missing today.
- **Solution approach:** Architectural pattern (e.g., new service + API surface) without prescribing code.

## Change Isolation Strategy
- **Isolation principle:** e.g., "Layer behind `FeatureToggleService` to avoid cross-cutting edits."
- **Extension pattern:** Hook, module, or interface expected (`@lib/services/feature/mod.rs`).
- **Stability assurance:** Tests, feature flags, or guards preventing regressions.

## Success Criteria
✅ Observable behaviour shifts
✅ Specific data/UX outcomes
✅ Monitoring/logging expectations
✅ Manual and automated validation requirements

## Never Do (Protection Boundaries)
❌ Files or contracts that must remain untouched
❌ Anti-patterns that break compatibility
❌ Shortcuts (e.g., bypassing feature flags, ignoring error handling)

## Technical Architecture
Describe system boundaries, data flow, and integration points. Reference directories with `@` markers. Offer miniature diagrams or bullet hierarchies when useful. Keep guidance architectural—no code or command snippets in the wish output.

## Task Decomposition
For each task group capture:
- **Group Name:** short slug (e.g., `foundation-resolver`).
- **Goal:** Outcome produced.
- **Context to Review:** Required @ references (files, directories, docs).
- **Creates / Modifies:** Expected file paths created or edited.
- **Evidence:** Tests, logs, QA steps, or manual checks proving success.
- **Dependencies:** Upstream sequencing and prerequisites.
- **Hand-off Notes:** Contracts or artefacts next groups rely on.

### Scenario Blueprint Catalog
Tailor these patterns to the wish scope. Provide high-signal guidance only.

#### New Feature (Full-Stack)
- **Group A – Domain & Contracts**
  - Goal: Establish data models, service interfaces, toggles.
  - Context: @lib/services/user_notifications/, @lib/models/, @shared/types.ts.
  - Creates / Modifies: lib/services/user_notifications/mod.rs, shared types regeneration plan, feature flag config.
  - Evidence: Prepared regression (`uv run pytest tests/lib/test_user_notifications.py -q`), contract notes.
  - Dependencies: None.
  - Hand-off Notes: Share DTO names and toggles for API/UI groups.
- **Group B – API Surface**
  - Goal: Expose backend endpoints with permission safeguards.
  - Context: @crates/server/src/routes/notifications.rs, @crates/server/src/services/user_service.rs, @frontend/src/lib/api/client.ts.
  - Creates / Modifies: Server routes, OpenAPI outline, API client modules.
  - Evidence: `uv run pytest tests/api/test_notifications.py -q`, Postman smoke checklist.
  - Dependencies: Group A contracts.
  - Hand-off Notes: Publish endpoint schema and error model for UI hand-off.
- **Group C – Frontend Experience**
  - Goal: Render UI, wire API calls, manage state.
  - Context: @frontend/src/components/dashboard/, @frontend/src/hooks/useNotifications.ts, @frontend/src/lib/state/.
  - Creates / Modifies: Notification components, hooks, feature gating.
  - Evidence: `pnpm run test notifications`, manual QA plan for forge-qa-tester.
  - Dependencies: Groups A & B.
  - Hand-off Notes: Provide UX notes and accessibility checks for QA.

#### Bug Fix (Regression)
- **Group A – Reproduction & Guardrail**
  - Goal: Capture failing behaviour in automated tests.
  - Context: @tests/lib/test_worktree_manager.py, @crates/utils/src/worktree_manager.rs, incident logs.
  - Creates / Modifies: Regression test case, fixtures/mocks.
  - Evidence: Document failing `uv run pytest tests/lib/test_worktree_manager.py -k regression -q` output.
  - Dependencies: None.
  - Hand-off Notes: Share failure signature for remediation.
- **Group B – Remediation**
  - Goal: Patch defect with minimal surface area.
  - Context: @crates/utils/src/worktree_manager.rs, @crates/utils/src/logging.rs.
  - Creates / Modifies: Target module adjustments, guard conditions, messaging.
  - Evidence: Regression passes, targeted smoke output recorded.
  - Dependencies: Group A tests.
  - Hand-off Notes: Outline risk areas for QA.
- **Group C – Verification & Monitoring**
  - Goal: Validate fix in situ and update monitoring.
  - Context: @genie/reports/forge-tests-*, @scripts/monitoring/, incident ticket.
  - Creates / Modifies: QA checklist, alert thresholds, rollback notes.
  - Evidence: Manual reproduction notes, log excerpts, dashboard screenshots.
  - Dependencies: Groups A & B.
  - Hand-off Notes: State post-release validation tasks.

#### Data Migration (Backend)
- **Group A – Schema Design & Rollback**
  - Goal: Define forward/backward migration plan.
  - Context: @crates/db/migrations/, @crates/db/src/models/, @docs/architecture/data-migrations.md.
  - Creates / Modifies: Migration plan doc, rollback checklist, schema note.
  - Evidence: Dry-run result from `sqlx migrate run --dry-run` captured.
  - Dependencies: None.
  - Hand-off Notes: Provide downtime expectations and owner list.
- **Group B – Migration Implementation**
  - Goal: Author SQL and adjust ORM/services.
  - Context: @crates/db/src/models/user.rs, @crates/server/src/services/user_service.rs, @shared/types.ts.
  - Creates / Modifies: Migration file, Rust structs, ts-rs regeneration plan.
  - Evidence: `sqlx migrate run`, `cargo test -p db --lib`, ts-rs output documented.
  - Dependencies: Group A blueprint.
  - Hand-off Notes: Document new schema version and feature flag requirements.
- **Group C – Backfill & Ops Validation**
  - Goal: Populate historical data and confirm system health.
  - Context: @scripts/backfill/, @crates/executors/src/jobs/, ops runbooks.
  - Creates / Modifies: Backfill script, cron/job config, monitoring dashboards.
  - Evidence: Dry-run logs, before/after row counts, rollback readiness.
  - Dependencies: Migration applied (Group B).
  - Hand-off Notes: Provide completion criteria and alert thresholds.

#### Configuration / Feature Toggle Change
- **Group A – Configuration Survey**
  - Goal: Map existing toggles and dependencies.
  - Context: @lib/config/settings.rs, @frontend/src/lib/config/, @docs/configuration/feature-flags.md.
  - Creates / Modifies: Config audit note, risk matrix, owner list.
  - Evidence: Capture current toggle states with CLI/log output references.
  - Dependencies: None.
  - Hand-off Notes: Clarify rollout sequencing and rollback path.
- **Group B – Implementation & Rollout Plan**
  - Goal: Update configs, scripts, documentation.
  - Context: Same as survey plus @scripts/deploy/, @docs/releases/.
  - Creates / Modifies: Config files, deployment scripts, release checklist.
  - Evidence: `pnpm run build`, `uv run python scripts/check_config.py`, dry-run logs summarized.
  - Dependencies: Survey complete.
  - Hand-off Notes: Provide human runbook for toggling and post-deploy checks.

Expand this catalog as new wish archetypes emerge (performance, infra hardening, compliance). Always define discovery scope, change surface, verification, and hand-offs.

## Open Questions & Assumptions
Track unknowns, competing options, or items needing human confirmation. Each assumption must include its rationale and the validation plan during execution.

## Blocker Protocol
Executors issue a Blocker Testament (`genie/reports/blocker-<group-slug>-<timestamp>.md`) when runtime discovery contradicts the plan. Document notification paths, turnaround expectations, and how the wish will be revised before work resumes.

## Status Log
Maintain timestamped entries for revisions, approvals, and significant decisions so future sessions can resume with shared context.

## Guidance for Executors
- Re-read every referenced file and diagnostic before coding.
- Coordinate with Genie if runtime context demands a pivot; never self-authorize deviations.
- Capture rationale, commands run, and outcomes in Death Testaments referencing validated wish sections.
- Remember: wish output is architectural guidance—no code or command snippets appear in the wish file itself.

## Reporting Expectations
- Close each `/wish` response with a numbered chat summary and the final wish path.
- Subsequent orchestration (`/forge`, agent prompts) must reference the latest wish version.
- Once status is `APPROVED`, the wish becomes the architectural contract; executors own real-time strategy within its guardrails.

## Behavioural Reminders
- Follow Evidence-Based Thinking: investigate, analyse, evaluate, then respond.
- Celebrate human insight; invite clarifications whenever uncertainty remains.
- Keep workspace tidy—edit existing wish files instead of creating variants.

A wish is a human-guided EPIC. Map where to explore, what to deliver, and how to prove success—then let specialist agents bring the implementation to life.
