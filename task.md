# Task: Bring Discord Integration To WhatsApp Parity (Users, Traces, Linking)

<goal>
Elevate the Discord integration to match WhatsApp’s standards and patterns: persist users, message_traces, and trace_payloads; ensure consistent routing, observability, and identity linking so one human can be recognized across platforms (Discord, WhatsApp) under a single agent presence.
</goal>

<context_gathering>
Goal: Get enough context fast. Parallelize discovery and stop as soon as you can act.

Method:
- Start broad, then fan out to focused subqueries aligned to WhatsApp patterns (users, traces, payloads, routing, identity linking).
- In one batch, read top references for Discord and WhatsApp; deduplicate; cache mental map; do not re-open files unless necessary.
- Avoid over-searching. Stop as soon as you can name exact codepaths to modify and the target shape of new code.

Early stop criteria:
- You can name the exact files/functions to change for: inbound Discord handling, outbound Discord sending, message_traces writes, trace_payloads writes, user creation/lookup, and identity linking.
- Top hits converge (~70%+) on a single path per responsibility (e.g., ChannelHandler + MessageRouter for routing, DB/service layer for traces).

Escalate once:
- If patterns between WhatsApp and Discord conflict or scope is fuzzy, run one refined, parallel search focusing on: message_traces writes, trace_payloads writes, user creation/lookup semantics, and cross-channel identity linking.

Depth:
- Trace only the symbols you will modify or whose contracts you rely on (ChannelHandler, MessageRouter, Agent API client, DB trace writers). Avoid transitive expansion.

Loop:
- Batch search → minimal plan → implement → validate.
- Search again only if validation fails or new unknowns appear. Prefer acting over more searching.
</context_gathering>

<tool_preambles>
- Begin by restating the immediate sub-goal (e.g., “Locate WhatsApp trace persistence”).
- Then outline the one or two actions you’ll take next (e.g., “Open handlers.py; find trace writer util”).
- Update succinctly at each logical checkpoint (investigate → patch → validate). Keep messages 1–2 sentences.
- Summarize completed work distinctly from planned work when a subtask finishes.
</tool_preambles>

<persistence>
- Keep going until Discord reaches WhatsApp parity for: user creation, message_traces, trace_payloads, and identity linking across platforms.
- Do not stop on uncertainty; decide the most reasonable approach based on WhatsApp patterns and proceed. Document assumptions.
- Only hand back for review after implementation, validation, and a short ops guide are complete.
</persistence>

<reasoning_effort>
- Reasoning: medium. Prefer decisive action guided by WhatsApp patterns.
- Verbosity: low for chat updates; high clarity in code and commit messages.
- One refined search batch maximum before coding, unless validation fails.
</reasoning_effort>


# Scope & Success Criteria

## Outcomes (Definition of Done)
- Users: Incoming Discord messages create or resolve a user consistent with WhatsApp rules; user persistence exists and the same human can be linked across WhatsApp and Discord.
- Tracing: Every inbound and outbound Discord message writes a row to message_traces with channel_type="discord", plus a linked trace_payloads row containing normalized/raw payload as per WhatsApp.
- Parity: Data shape mirrors WhatsApp’s semantics (fields, flags like has_media/has_quoted_message, direction, status), with Discord-specific extensions where necessary.
- Routing: Discord routes through MessageRouter with the same contracts used by WhatsApp (session_name, session_origin="discord", media handling, agent selection), with stream/non-stream behavior aligned.
- Observability: Logging fields and telemetry match WhatsApp’s style and surface key IDs (trace_id, message_id, user_id, instance name, channel_type) for quick correlation.
- Docs: README or channel-specific docs updated to describe Discord parity, identity linking model, and operational checks.

## Non-Goals (for now)
- Full media parity beyond basic images/files if not already present in WhatsApp parity path.
- Admin UI for identity linking (provide API/model; UI is optional unless trivial).
- Any unrelated refactors outside Discord/WhatsApp parity scope.


# Context Snapshot (for orientation; verify in repo)
- Discord handler: `src/channels/discord/channel_handler.py` (mention detection, chunking, calls `message_router.route_message`).
- Discord sending: `src/channels/message_sender.py` (Discord paths and socket connector usage); `src/channels/discord/bot_manager.py` if present (check).
- WhatsApp reference: `src/channels/whatsapp/handlers.py` (patterns for user creation/lookup, tracing, payload persistence, session naming, origin type, media), plus any WhatsApp-specific streaming helpers.
- Routing: `src/services/message_router.py` (shared contracts for message_text, user, session_name, session_origin, media, trace_context; agent API client usage).
- Tracing/DB:
  - message_traces and trace_payloads appear in migrations/scripts: `scripts/migrate_sqlite_to_postgres.py`, Alembic versions under `alembic/versions/*`.
  - Check for helper/services that write traces/payloads (search “message_traces”, “trace_payloads”).
  - Telemetry client: `src/core/telemetry.py` (ensure consistency with traces where applicable).
- Process manager & sockets: `ecosystem.config.js`, `scripts/setup_ipc_sockets.sh` (Discord socket paths); keep parity but not required to change architecture.


# Target Architecture & Data Shape

## Discord Parity Model
- Channel type: `discord`.
- Session origin: `discord`.
- Session naming: Prefer `discord_{guildId}_{userId}` for guild messages and `discord_dm_{userId}` for DMs; mirror WhatsApp’s conventions for stability.
- User dictionary: Include stable Discord identifiers and human-friendly fields:
  - identifiers: `{ provider: 'discord', user_id: <discord_user_id>, guild_id?: <guild_id> }` (plus WhatsApp’s pattern for phone/jid on that side).
  - user_data: `{ name, username, discriminator?, guild_name?, channel_id, channel_name }`.
  - Avoid requiring PII not available from Discord (e.g., email) unless OAuth exists.

## message_traces (each inbound/outbound event)
- Required parity fields with WhatsApp: `trace_id`, `instance_name`, `channel_type='discord'`, `direction` ('inbound'|'outbound'), `message_id` (Discord message id), `session_name`, `user_id` (internal user), timestamps, success flags (e.g., `agent_response_success`), and booleans (`has_media`, `has_quoted_message`) when applicable.
- For outbound, set status fields indicating send success/failure; capture message ids where possible.

## trace_payloads (raw or normalized payloads)
- One row per message_trace; reference `trace_id`.
- Store the canonical raw payload (Discord event/message dict and outbound request data) and normalized envelope if WhatsApp uses one.
- Flags: `contains_media`, `contains_base64` as per WhatsApp; adapt for Discord attachments.

## Identity linking across platforms
- Introduce or reuse a minimal linking schema to associate one internal user across providers:
  - Table (or model) like `user_external_ids(user_id, provider, external_id, extra)`; unique on `(provider, external_id)`.
  - On inbound Discord, resolve or create internal user and upsert a link row for `(discord, discord_user_id)` (plus `guild_id` in `extra` as needed).
  - On inbound WhatsApp, similarly upsert `(whatsapp, jid or phone)`.
  - Provide lookup path: try to match incoming Discord external id to an existing linked internal user before creating a new user.


# Implementation Plan

## Phase 1 — Investigate & Map (time-boxed)
- WhatsApp: Identify exact code that writes to message_traces and trace_payloads and the data shape/flags used. Note how user creation/lookup happens, and how session_origin/session_name are formed.
- Discord: Confirm current inbound flow (mention detection, content extraction) and outbound paths. Note where we can hook trace writes and user linking without architectural churn.
- DB: Verify migrations/models exist for message_traces/trace_payloads; list fields and constraints that WhatsApp uses so Discord matches.
- Output: A short mapping doc (in repo, e.g., docs/discord_parity.md) with side-by-side WhatsApp vs Discord responsibilities and exact files/functions to patch.

## Phase 2 — Data Contracts & Utilities
- Define/extend minimal utilities for:
  - Creating a `message_trace` (inbound/outbound) with channel_type='discord'.
  - Creating a `trace_payload` row paired to the trace id.
  - Extracting Discord message id, attachments presence, quoted reference presence, and normalized payload structure.
- If WhatsApp already has helpers, factor common code to a shared util where reasonable (do not overshoot scope).

## Phase 3 — Inbound Discord Handling
- In `src/channels/discord/channel_handler.py`:
  - Before routing, build or resolve user using identity-linking lookup. If not found, create user via Agent API and immediately upsert `(discord, discord_user_id)` into the linking table.
  - Create inbound `message_trace` and a corresponding `trace_payload` for the raw event. Set flags `has_media`, `has_quoted_message` when applicable.
  - Route to `MessageRouter` with `session_origin='discord'`, `session_name` pattern above, and `media_contents` if attachments exist.

## Phase 4 — Outbound Discord Sending
- In `src/channels/message_sender.py` (Discord paths) and/or `src/channels/discord/*` send routines:
  - After a successful send, write an outbound `message_trace` with `channel_type='discord'`, link a `trace_payload` capturing send payload/response, and set success fields.
  - On failure, still create a trace with error details; mark success flags accordingly.

## Phase 5 — Identity Linking
- Add the `user_external_ids` (or equivalent) model/migration if not present. Minimal fields: `id`, `user_id`, `provider`, `external_id`, `extra` (JSON), created/updated timestamps; unique `(provider, external_id)`.
- Implement helper functions to upsert link on inbound and to look up internal user by `(provider, external_id)`.
- Update Discord and WhatsApp inbound paths to use the lookup before creating a user.

## Phase 6 — Validation, Docs, Examples
- Add integration logs and a simple CLI or script to show the last N Discord traces and payloads for a given user/session to prove parity.
- Update README/docs for: configuration, expected data flow, identity linking behavior, and operational checks.
- Provide a short runbook for troubleshooting (permissions, socket connection, rate-limits, missing intents).


# Acceptance Criteria (Testable)
- When mentioning the bot in a guild, an inbound message_trace is written with `channel_type='discord'`, `direction='inbound'`, `message_id=<discord_message_id>`, and a linked trace_payload containing the raw event JSON.
- The router produces an agent response; the outbound send creates a corresponding outbound message_trace and trace_payload.
- Sending a DM to the bot produces the same behavior with `session_name='discord_dm_<userId>'`.
- If the same human has an existing WhatsApp user, creating a `(discord, discord_user_id)` link results in both channels resolving to the same internal user_id.
- Flags like `has_media` and `has_quoted_message` are correctly set for Discord where applicable (attachments / message references).
- Logs include `trace_id`, `user_id`, `instance_name`, `channel_type`, and `message_id` for both inbound and outbound.


# Risks & Mitigations
- Permissions/Intents: Ensure `message_content` intent is enabled and invite URL permissions are correct; document failures clearly.
- Rate limits: Use the existing chunking; add brief delays on multi-chunk sends.
- Payload size: Store payloads efficiently; if too large, store a normalized subset plus a pointer to raw where feasible.
- Migration: If adding `user_external_ids`, provide a safe Alembic migration and idempotent upsert logic.


# Execution Rules (Agent)
- Follow repository coding standards; keep changes minimal and focused.
- Do not refactor unrelated code; extract shared helpers only when it reduces duplication between WhatsApp/Discord traces.
- Prefer small, reviewable PRs per phase if possible; otherwise, commit logically grouped changes.
- Validate locally with targeted tests on Discord inbound/outbound flows.


# Step-by-Step Checklist
- [ ] Map WhatsApp trace/payload/user patterns and list exact functions to mirror.
- [ ] Identify Discord hook points for inbound/outbound traces.
- [ ] Implement trace writers and payload persistence for Discord inbound.
- [ ] Implement trace writers and payload persistence for Discord outbound.
- [ ] Add/verify identity linking model and helpers; wire into inbound paths.
- [ ] Update docs and add a quick inspection script for traces.
- [ ] Validate with guild mention and DM scenarios; confirm parity fields.


# Handover Notes
- Provide a short summary of the deltas vs. WhatsApp where Discord differs (e.g., user identifiers, quoted messages, media specifics).
- Include follow-ups for deeper media parity, message edits, reactions, and thread support if desired in later iterations.

