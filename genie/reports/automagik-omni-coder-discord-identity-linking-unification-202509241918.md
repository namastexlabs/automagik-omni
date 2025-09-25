# Automagik Omni Coder • Death Testament

Title: feat: discord identity linking unification
Slug: discord-identity-linking-unification
When (UTC): 2025-09-24 19:19:08
Branch: feat/discord-identity-linking

## Scope
- Add `user_external_ids` model and Alembic migration to support cross-channel identity mapping.
- Implement shared helpers in `user_service` to link and resolve external IDs.
- Ensure WhatsApp flow creates/maintains WhatsApp external link on user upsert.
- Update Discord inbound to resolve existing local user via Discord external ID before routing.
- Add tests proving cross-channel user_id reuse and WhatsApp link creation.

## Files Touched
- `src/db/models.py` — Added `UserExternalId` model + relationship.
- `alembic/versions/7f3a2b1c9a01_create_user_external_ids_table.py` — New migration creating table.
- `src/services/user_service.py` — Added `link_external_id`, `resolve_user_by_external`; wired into phone upsert.
- `src/channels/discord/bot_manager.py` — Resolve local user by Discord ID and pass `user_id` to router.
- `tests/test_identity_linking.py` — New tests for linking + resolution.

## Migration Preview
DDL (conceptual):
- create table `user_external_ids` (
  id serial PK,
  user_id varchar FK -> users.id ON DELETE CASCADE,
  provider varchar not null,
  external_id varchar not null,
  instance_name varchar null FK -> instance_configs.name,
  created_at timestamp not null,
  updated_at timestamp not null,
  unique (provider, external_id)
)

Upgrade safety:
- Pure additive table creation; no writes to existing tables. Safe forward.

Downgrade safety:
- Drops `user_external_ids` (data loss limited to links only). Documented and acceptable.

## Validation
Commands run (failure ➜ success where applicable):
- uv run pytest -q
  - Result: 340 passed, 4 skipped
- Targeted tests:
  - uv run pytest tests/test_identity_linking.py -q
    - Result: 3 passed

Manual checks:
- WhatsApp handler uses `get_or_create_user_by_phone` which now ensures a WhatsApp link.
- Discord bot_manager performs a best-effort resolution by `discord_id`; if found, sets `user_id`, else falls back to prior behavior and does not create local users (schema requires phone fields).

## Behaviour Notes
- WhatsApp semantics unchanged; additional link creation is idempotent.
- Discord now reuses a local `users.id` when a link exists; otherwise, no local record is created (by design, due to mandatory WhatsApp fields). This avoids duplicate local users and satisfies unification.

## Risks
- Alembic migration timestamps use application-managed timestamps, not DB server defaults. If strict server defaults are desired, a follow-up migration can add `server_default` to timestamps.
- Uniqueness scoped to `(provider, external_id)` globally. If guild-scoped Discord IDs are later required, adjust uniqueness and helper semantics accordingly.

## Follow-ups (for Genie to delegate)
- Consider admin tooling to create/manage links (e.g., tie Discord IDs to known WhatsApp users).
- Optional: Add server-default timestamps to `user_external_ids` in production DBs.
- Extend Discord flow to backfill link upon authoritative correlation (e.g., a verified handshake), if needed.

## Evidence Artifacts
- Test output embedded above (`pytest` summaries).
- Code diffs in files listed under “Files Touched”.

