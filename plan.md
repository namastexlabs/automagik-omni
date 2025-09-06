Objective

- Redesign identity to support multiple integrations without polluting the core user model. Keep tracing/routing stable. Iterate only on the plan until approved.

DB Reality Check (Current)

- Tables present: `users` (WhatsApp-centric), `message_traces`, `trace_payloads`, `instance_configs` (with Discord rows).
- `message_traces` is WA-shaped (evolution_* fields); payload details live in `trace_payloads` JSON.
- Goal: Avoid schema churn in traces now; focus on a clean identity layer that coexists with current data.

Key Principles

- Single canonical user per human; minimum required attributes.
- Provider identifiers are stored on the user (no separate integration table in this design).
- A user may have multiple provider handles populated (e.g., WhatsApp + Discord).
- Additive, backward-compatible migrations; phase changes safely with a transition window.

Identity Data Model (Revised — Users-Centric with Provider Handles)

- `users` (single source of truth, enriched)
  - Purpose: Keep human-readable provider IDs directly at the user level for straightforward association and queries.
  - Columns (target state):
    - Core: `id` (uuid pk, keep), `user_name` (new), `attrs` (JSON, generic future-proof), `agent_user_id?`, `last_session_name_interaction?`, `instance_name`, timestamps.
    - Provider handles (nullable, indexed): keep `whatsapp_jid`; add `discord_username`; optionally store `discord_user_id` for reliability; maintain `handles` (JSON) for other providers.
  - Remove/Deprecate: `last_seen_at`, `message_count`. Rename `display_name` → `user_name` (compat during transition).
  - Constraints/Indexes: `(instance_name, whatsapp_jid)` unique when not null; `(instance_name, discord_username)` unique when not null; index `agent_user_id`.
  - Per-user Hive agent assignment (override): `assigned_agent_id?`, `assigned_agent_type?` ('agent'|'team'), `assigned_agent_origin?` ('hive'|'automagik'), `assigned_instance_name?`.

- Message traces: keep existing tables `message_traces` and `trace_payloads` for this iteration.
  - Continue storing provider-specific details (like WhatsApp jid) in existing fields.
  - For Discord parity, store Discord specifics inside `trace_payloads.payload` JSON; defer schema-level `channel_type/direction` until a dedicated observability migration.

Why this layout

- Matches the requirement to store human-readable IDs (phone numbers, usernames) at the user level for association.
- Avoids immediate table sprawl by using a `handles` JSON map for long tail providers.
-- Supports performance by adding indexed columns only for major providers (WhatsApp, Discord) while staying extensible.
- Enables per-user Hive agent assignment without changing global instance config.

Service/API Layer Changes

- New: `user_identity_service`
  - `get_or_create_user_by_handle(provider, human_id, instance_name, attrs)` → resolves via `(instance_name, whatsapp_jid)` or `(instance_name, discord_username)` first; fallback to `handles` JSON.
  - `attach_agent_user(user_id, agent_user_id)` → store authoritative mapping.
  - `set_assigned_agent(user_id, assigned_agent_id, agent_type='agent', origin='hive', assigned_instance_name=None)` → per-user routing override.
  - `merge_users(primary_user_id, secondary_user_id)` → unify handles and counters (admin path).

- WhatsApp inbound
  - Resolve via `get_or_create_user_by_handle('whatsapp', whatsapp_jid, instance_name, {user_name,...})`.
  - After agent response, `attach_agent_user` if present.

- Discord inbound
  - Resolve via `get_or_create_user_by_handle('discord', discord_username, instance_name, {guild_id, channel_id, ...})`; optionally store discord_user_id.
  - After agent response, `attach_agent_user` if present.

Migration Strategy (Users-Centric, Backward-Compatible)

Phase A — Add columns (no breaking changes)
- Alter `users` to add: `user_name`, `attrs` (JSON), `agent_user_id?`, `discord_username`, optional `discord_discriminator?`, optional `discord_user_id?`, `handles` (JSON), `assigned_agent_id?`, `assigned_agent_type?`, `assigned_agent_origin?`, `assigned_instance_name?`.
- Backfill (idempotent): map `display_name`→`user_name`; set `handles.whatsapp` from `whatsapp_jid`; if `last_agent_user_id` exists, set `agent_user_id`.

Phase B — Resolution switch (compat window)
- WhatsApp inbound: resolve by `(instance_name, whatsapp_jid)`; maintain legacy writes for safety during rollout.
- Discord inbound: resolve by `(instance_name, discord_username)`; on first contact, create user and populate handle columns (+ store `discord_user_id`).

Phase C — Cleanup
- All identity reads prefer handle columns, then `handles` JSON fallback.
- Deprecate WA-only legacy columns (`phone_number`, `display_name`, etc.) and schedule a later drop after stability.

Routing & Tracing (Parity Targets)

- Routing contracts unchanged; just pass `session_origin` consistently (`whatsapp`/`discord`) and `session_name` as per channel rules.
- Tracing (no schema change now):
  - Inbound Discord: create trace and write `webhook_received` payload with normalized event JSON; set parity flags in payload JSON.
  - Outbound Discord: log `discord_send` payloads in `trace_payloads`. Analytics columns can come later if needed.

Observability

- Standardize log keys: `trace_id`, `provider`, `message_id`, `instance_name`, `session_name`, `user_id`, `agent_user_id?`.
- Add one CLI/readme doc to query last N traces by `session_name` prefix (optional).

Acceptance Criteria (Updated)

- Identity resolution: Given inbound Discord or WhatsApp, resolve a stable `users.id` directly via provider handle columns or `handles` JSON fallback.
- Cross-channel linking: The same person on Discord and WhatsApp maps to the same `core_user` after agent supplies `user_id` or via admin merge; subsequent messages resolve to that user.
- Tracing: Discord inbound/outbound events create `message_traces` and `trace_payloads` rows with provider payloads stored in JSON and parity flags set.
- No breaking changes: WhatsApp continues to operate during the migration window (dual-write) until full switch-over.

Implementation Steps

1) Schema
- Alembic: alter `users` (add columns/indexes); provide idempotent backfill.

2) Services
- Implement `user_identity_service` with: get-or-create by handle, attach_agent_user, set_assigned_agent, merge_users.

3) Handlers
- WhatsApp: switch to `user_identity_service` (keep legacy writes during rollout).
- Discord: implement inbound using `user_identity_service`.

4) Tracing Parity
- Add Discord trace writes using existing `trace_service` and JSON payloads; no schema changes.

5) Observability & Docs
- Update docs explaining the new identity model, migration path, and operational checks.

Risks & Mitigations

- Split-brain identities during migration → mitigate with `merge_users` admin tool and agent_user_id attachment.
- Instance scoping: the same external_id across different instances → include `instance_name` in uniqueness to avoid unintended collisions.
- Performance: JSONB growth in `user_integrations.data` → index only required keys later; keep core indexed columns minimal now.

Decision Points for You

- Table names: `core_users` vs repurposing `users` (I recommend new `core_users` to avoid confusion and enable staged cutover).
- Uniqueness scope: enforce `unique(provider, external_id, instance_name)` (safer for multi-tenant) vs `unique(provider, external_id)` (global identity per provider).
- Attach `agent_user_id` on `core_users` now or later (I recommend now; it simplifies cross-channel resolution and auditability).

Identifier Reality (from code + DB)

- WhatsApp (today):
  - Unique in code: `phone_number` per `instance_name` for users table (user_service.get_or_create_user_by_phone).
  - JID: `whatsapp_jid` present and used in traces and helpers; reliable canonical representation.
  - Plan: keep `whatsapp_jid` as canonical; continue accepting phone_number at edges but normalize to jid; no need to add `whatsapp_e164` now.

- Discord (today):
  - Unique in code: numeric `author.id` (snowflake) is used for session_name and payloads; no DB persistence currently.
  - Human-readable: `user.name` (Discord username) used for display; can change but modern Discord usernames are globally unique. We’ll store both.
  - Plan: add `discord_user_id` (for reliable matches) and `discord_username` (for human-readable association) on users; primary matching uses `discord_user_id` with `discord_username` as secondary/display.

- Dead/low-value fields in users:
  - `last_seen_at`, `message_count`: updated only in user_service; not used anywhere else. Mark deprecated and remove in a subsequent migration; if needed, mirror future counters in `attrs` JSON.
  - `display_name`: used but replaced by `user_name` (keep temporarily for compatibility).
