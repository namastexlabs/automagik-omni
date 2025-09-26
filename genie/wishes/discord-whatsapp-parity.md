# 🧞 Discord WhatsApp Parity WISH

**Status:** DRAFT

## Executive Summary
Elevate the Discord integration to persist users, traces, and payloads with the same contracts WhatsApp relies on so a single human identity flows cleanly across channels.

## Current State Analysis
**What exists:** Discord handlers route inbound messages and send responses without writing `message_traces`, `trace_payloads`, or shared user links; WhatsApp paths already provide full persistence, router context, and telemetry.
**Gap identified:** Discord lacks parity for user creation/lookup, trace persistence, normalized payload storage, session naming, and identity linkage, producing fragmented observability and duplicate humans.
**Solution approach:** Apply WhatsApp parity patterns to Discord by introducing trace writers, payload persistence, identity linking helpers, and documentation updates while preserving existing routing surfaces.

## Change Isolation Strategy
- **Isolation principle:** Localize persistence changes within Discord channel modules, shared services, and new identity helpers without touching unrelated channels.
- **Extension pattern:** Reuse WhatsApp abstractions where possible; add Discord-specific adapters rather than rewriting shared router or DB layers.
- **Stability assurance:** Gate new behavior behind channel-type checks and maintain existing WhatsApp flows by mirroring, not altering, their contracts.

## Success Criteria
✅ Inbound and outbound Discord traffic writes `message_traces` rows with `channel_type="discord"` and linked `trace_payloads` entries.
✅ Discord inbound path resolves or creates users following the same identity rules as WhatsApp, including cross-channel linking.
✅ MessageRouter receives consistent session metadata (name, origin, trace context) for Discord and WhatsApp with validated logs.
✅ Documentation explains Discord parity flow, linking behavior, and operational verification steps.

## Never Do (Protection Boundaries)
❌ Modify WhatsApp tracing logic except for shared helper extraction that keeps semantics identical.
❌ Introduce direct database writes outside existing ORM/service patterns.
❌ Ship without Red→Green→Refactor validation proving trace persistence and identity linking.

## Technical Architecture

### Component Structure
- `src/channels/discord/channel_handler.py`: Inbound Discord event handling, media normalization, router invocation.
- `src/channels/message_sender.py` & `src/channels/discord/bot_manager.py`: Outbound dispatch with access to Discord connector.
- `src/services/message_router.py`: Shared routing service; ensures Discord parity for session metadata and trace context.
- `src/services/trace_service.py` (or equivalent WhatsApp helper): Reference patterns for writing `message_traces` and `trace_payloads`.
- `src/services/user_service.py` & related models: Existing user persistence to mirror for Discord identities.
- `migrations/` + potential `user_external_ids` model: Storage for cross-channel links.

### Data Flow Overview
1. **Inbound Discord event** → channel handler → user lookup/linker → trace writer → router.
2. **Router response** → outbound sender → Discord API → trace writer with payload/result.
3. **Identity linking** ensures `(provider, external_id)` mapping unifies Discord and WhatsApp humans.
4. **Telemetry/logging** emits trace identifiers for observability dashboards.

### Contracts & Interfaces
- Maintain MessageRouter contract: `route_message(user, session_name, session_origin, trace_context, media, text)`.
- Trace records mirror WhatsApp schema: direction, message_id, has_media, has_quoted_message, payload reference.
- Identity linker exposes `resolve_user(provider, external_id)` and `upsert_link(user_id, provider, external_id, extra)` semantics.

## Development Phases
- **Phase 1 — Discovery & Pattern Mapping:** Audit WhatsApp tracing, payload, and user flows; catalog Discord touchpoints needing parity.
- **Phase 2 — Inbound Trace Persistence:** Implement Discord inbound trace + payload writes with raw event capture and normalized metadata.
- **Phase 3 — Outbound Trace Persistence:** Add outbound trace/payload records covering success and error cases with Discord-specific payload shapes.
- **Phase 4 — User & Session Parity:** Mirror WhatsApp user lookup/creation, align session naming/origin, and integrate trace context through MessageRouter.
- **Phase 5 — Identity Linking:** Introduce or extend `user_external_ids` model, helpers, and Discord usage; ensure WhatsApp path consumes the shared helper.
- **Phase 6 — Validation & Documentation:** Execute automated tests, manual message flows, and update parity docs plus operational runbook.

## Validation Plan
- `uv run pytest tests/channels/discord/test_channel_handler.py` (extend or create) covering inbound trace + user behaviors.
- `uv run pytest tests/channels/test_message_sender.py::TestDiscordSender` verifying outbound trace records and failure handling.
- `uv run pytest tests/services/test_identity_linking.py` validating linker helpers and cross-channel resolution.
- Manual guild mention + DM against staging bot, confirm `message_traces` and `trace_payloads` rows plus logs show shared user_id.
- Optional script: `uv run python scripts/show_recent_traces.py --channel discord --limit 5` to demonstrate parity.

## Evidence Requirements
- Test outputs demonstrating new/updated pytest cases pass.
- Database snapshots or ORM query logs proving `message_traces` and `trace_payloads` rows for Discord events.
- Application logs highlighting aligned trace metadata (trace_id, user_id, session_origin="discord").
- Documentation diff referencing parity guidance and runbook steps.

## Task Decomposition
- **Group A — Parity Research:** WhatsApp reference mapping, Discord touchpoint inventory, alignment notes.
- **Group B — Inbound Persistence:** Implement inbound trace writer, payload storage, and logging updates.
- **Group C — Outbound Persistence:** Persist outbound traces/payloads, handle retries, and error logging.
- **Group D — Identity Linking:** Introduce/link `user_external_ids`, update Discord/WhatsApp lookups, add helpers + tests.
- **Group E — Docs & Tooling:** Update README/channel docs, add trace inspection script, capture validation evidence.

## Open Questions & Assumptions
- **Assumption:** WhatsApp parity patterns remain source of truth; no breaking changes pending.
- **Assumption:** Database schema can accept `user_external_ids` addition without conflicting migrations.
- **Question:** Do we require media payload storage for Discord attachments beyond metadata (size, URL)?
- **Question:** Should identity linking expose admin tooling or remain API-only for this wish?

## Dependencies & Partners
- Coordinate with data/infra owners for migration review (`user_external_ids`).
- Confirm with observability owners that new Discord trace fields integrate with dashboards.
- Notify QA to design multi-channel regression scenarios once implementation begins.

## Documentation Targets
- Update channel parity section in `docs/integrations/discord.md` (or equivalent) with trace + linking behavior.
- Extend runbook with verification steps for tracing, payload inspection, and identity linkage troubleshooting.
- Append wish status and evidence summary to `genie/wishes/discord-whatsapp-parity.md` during execution oversight.

