# 🧞 Discord Parity QA Validation WISH

**Status:** DRAFT

## Executive Summary
Deliver human-grade QA coverage for the Discord↔WhatsApp parity initiative, capturing end-to-end evidence that traces, payloads, and identity linking behave identically across channels with actionable documentation for operators.

## Current State Analysis
**What exists:** Discord parity implementation tasks (tests, trace persistence, identity linking) completed via forge Groups A–C with task IDs recorded in `@genie/reports/forge-master-discord-whatsapp-parity-202509241821.md`.
**Gap identified:** No consolidated QA validation proving parity in practice, and no runbook documenting verification procedures, troubleshooting, or acceptance evidence.
**Solution approach:** Execute comprehensive QA scenarios spanning automated tests and manual Discord flows, log every observation, and publish a runbook plus Death Testament summarizing outcomes and residual risks.

## Change Isolation Strategy
- **Isolation principle:** QA operates solely through testing surfaces (CLI/API/database/logs) without modifying production code.
- **Extension pattern:** Add documentation and evidence artefacts under `/docs/` and `genie/reports/` while preserving existing implementation branches.
- **Stability assurance:** Use read-only inspection for databases/logs, revert any temporary fixtures, and avoid altering baseline configurations.

## Success Criteria
✅ Automated suites (`uv run pytest …`) for Discord parity pass on branch `qa/discord-parity-validation`.
✅ Manual guild mention and DM flows generate `message_traces` + `trace_payloads` rows with shared `user_id` and expected metadata.
✅ Identity linking confirmed by cross-channel queries/logs referencing a single human.
✅ Runbook added under `docs/discord-parity-validation.md` (or existing doc) detailing validation steps, troubleshooting, and evidence capture.
✅ QA Death Testament stored at `genie/reports/automagik-omni-qa-tester-discord-parity-<UTC>.md` linking raw artefacts.

## Never Do (Protection Boundaries)
❌ Modify WhatsApp parity logic or Discord implementation during QA.
❌ Rely on outdated evidence; every claim must reference fresh logs/tests.
❌ Remove or overwrite prior Death Testaments or evidence from Groups A–C.
❌ Leak real Discord tokens or credentials in artefacts.

## Technical Architecture

### Systems Under Test
- `src/channels/discord/channel_handler.py`: Inbound normalization, trace triggers, identity linking hooks.
- `src/channels/message_sender.py`: Outbound dispatch and trace logging.
- `src/services/message_router.py`: Session metadata, routing contracts.
- `src/services/user_service.py` & `user_external_ids` models: Identity linking persistence.
- Database tables: `message_traces`, `trace_payloads`, `users`, `user_external_ids`.
- Observability/logging: Structured logs exposing `trace_id`, `user_id`, `channel_type`, `session_name`.

### Tooling & Environment
- Branch: `qa/discord-parity-validation` (spawned from `wish/discord-whatsapp-parity`).
- Commands: `uv run pytest …`, `uv run python <scripts>`, database inspection via repo-approved utilities (e.g., `uv run python scripts/db_shell.py`).
- Logging: tail application logs (`tail -f logs/omni.log`), capture excerpts with timestamps.
- Discord simulation: Use staging tokens or mock connector; document whichever approach is chosen.

## Development Phases
- **Phase 1 — Context Sync:** Review wish + forge reports, load Groups A–C Death Testaments, confirm implementation branches/commits.
- **Phase 2 — Automated Validation:** Run targeted pytest suites (existing + newly added) for Discord parity; collect outputs and rerun on fixes if needed.
- **Phase 3 — Manual Flow Verification:** Execute guild mention and DM scenarios, monitor traces/payloads, verify identity linking, capture logs and DB snapshots.
- **Phase 4 — Evidence Packaging:** Archive logs, screenshots, pytest outputs; compile structured QA report and update runbook documentation.
- **Phase 5 — Closure & Feedback:** Summarize outcomes, note defects or follow-ups, transition artifacts to Genie for orchestration.

## Validation Plan
- Automated: `uv run pytest tests/channels/discord/test_channel_handler.py`, `uv run pytest tests/channels/test_message_sender.py::TestDiscordSender`, identity suites, and any new regression packs.
- Database checks: `uv run python scripts/query_traces.py --channel discord --limit 10` (or equivalent) to verify records and linked payloads.
- Manual: Trigger inbound messages (guild mention + DM) via staging bot; confirm `message_traces.channel_type == "discord"`, `trace_payloads` contain normalized/raw payload, and `user_external_ids` maps Discord IDs to shared `user_id` used by WhatsApp.
- Logging: Capture log entries showing `trace_id`, `user_id`, `session_origin="discord"`, `direction` fields for both inbound and outbound.
- Documentation: Update parity runbook with step-by-step validation instructions, required credentials, and troubleshooting tips.

## Evidence Requirements
- Pytest transcripts (stored in `genie/reports/evidence/` or referenced via attachments).
- Screenshots or textual logs of Discord message flows and resulting database entries.
- SQL excerpts or ORM outputs confirming identity linking.
- Diff of documentation updates within `docs/`.
- QA Death Testament summarizing scenarios, results, and open issues.

## Task Decomposition
- **Group D.1 — Automated Regression Capture:** rerun and document pytest suites, note failures.
- **Group D.2 — Manual Flow Validation:** execute guild/DM scenarios, log trace/payload outcomes.
- **Group D.3 — Identity Linking Proof:** query database/logs for cross-channel `user_id` reuse.
- **Group D.4 — Documentation & Reporting:** update runbook, compile QA report, list follow-ups.

## Open Questions & Assumptions
- **Assumption:** Staging Discord tokens/instances are available; otherwise testers will mock connectors and note limitations.
- **Assumption:** Database access permitted for read-only verification.
- **Question:** Should QA include attachment/media scenarios or defer to follow-up wish?
- **Question:** Is there an automated script to reset trace tables between runs, or should QA manually isolate data?

## Dependencies & Partners
- Coordinate with implementation owners (Groups A–C) for any fixes emerging from QA findings.
- Notify observability/infra stakeholders if log fields require adjustments.
- Engage human operator for Discord credential provisioning.

## Documentation Targets
- `docs/integrations/discord.md` (or new `docs/discord-parity-validation.md`) updated with parity QA procedure.
- Append QA evidence summary and remaining risks to this wish file upon completion.
- Reference QA Death Testament in main wish before closure.

