# Discord ↔ WhatsApp Parity QA Runbook

This runbook captures the end-to-end validation process for Discord parity on branch `qa/discord-parity-validation`. Follow the phases below to reproduce the evidence gathered on 2025-09-24.

## Prerequisites
- Checkout branch `qa/discord-parity-validation` and ensure `.env` is populated with staging credentials.
- Apply pending Alembic migrations so the identity-linking tables exist:
  ```bash
  uv run alembic upgrade 7f3a2b1c9a01
  ```
- Verify tracing is enabled (`Tracing enabled: True` when running `uv run python - <<'PY' ...`).
- Create the evidence workspace if missing: `mkdir -p genie/reports/evidence/discord-parity`.

## Phase 2 — Automated Validation
Run the discord-focused suites with `uv run pytest` and archive the transcripts.

| Command | Notes | Transcript |
| --- | --- | --- |
| `uv run pytest tests/channels/test_discord_trace_parity.py` | Parity regression suite (3 pass) | `genie/reports/evidence/discord-parity/phase-2-pytest-discord-trace.txt` |
| `uv run pytest tests/test_omni_handlers.py::TestDiscordChatHandler` | Handler contract coverage (8 pass) | `genie/reports/evidence/discord-parity/phase-2-pytest-omni-handlers.txt` |
| `uv run pytest tests/test_identity_linking.py` | Cross-channel identity helpers (3 pass) | `genie/reports/evidence/discord-parity/phase-2-pytest-identity-linking.txt` |
| `uv run pytest tests/channels/discord/test_channel_handler.py` | Handler edge cases (2 pass) | `genie/reports/evidence/discord-parity/phase-2-pytest-channel-handler.txt` |
| `uv run pytest tests/channels/test_message_sender.py` | Discord sender trace logging (2 pass) | `genie/reports/evidence/discord-parity/phase-2-pytest-message-sender.txt` |

## Phase 3 — Manual Discord Flow Verification
Manual validation uses lightweight stubs to simulate Discord events while exercising the real trace and identity services.

1. **Simulate guild mention + DM flows**
   ```bash
   uv run python - <<'PY'
   # Copy the helper from genie/reports/evidence/discord-parity/phase-3-manual-flow.txt
   # (snippet triggers DiscordChannelHandler._handle_message twice)
   PY
   ```
   The helper stubs Discord objects, invokes `_handle_message`, and records parity output.

2. **Prime cross-channel identity link**
   ```bash
   uv run python - <<'PY'
   # Copy the helper from genie/reports/evidence/discord-parity/phase-3-identity-linking.txt
   # (snippet creates WhatsApp user, links Discord external ID, replays manual flow)
   PY
   ```
   Confirms that Discord messages reuse the WhatsApp-seeded `user_id` once the link exists.

3. **Inspect trace and payload artefacts**
   ```bash
   uv run python - <<'PY'
   # See docs/discord-parity-validation.md for the exact inspection snippet
   PY
   ```
   The inspection command summarises `message_traces` and `trace_payloads` entries. Evidence stored at `genie/reports/evidence/discord-parity/phase-3-trace-inspection.txt`.

4. **Verify `user_external_ids` linkage**
   ```bash
   uv run python - <<'PY'
   # Query user_external_ids table for the Discord ID under test
   PY
   ```
   Output saved at `genie/reports/evidence/discord-parity/phase-3-user-external-ids.txt` confirms the Discord user maps to the WhatsApp-originated record.

> **Note:** The helper scripts reside inline in the evidence files. Copy them into `manual_scripts/` (or run via heredocs) when re-executing the flow. They intentionally monkeypatch `message_router.route_message` to avoid external API calls while still exercising trace persistence.

## Evidence Log
- Automated pytest transcripts: `genie/reports/evidence/discord-parity/phase-2-*.txt`
- Manual flow outputs: `genie/reports/evidence/discord-parity/phase-3-manual-flow.txt`
- Identity linking verification: `genie/reports/evidence/discord-parity/phase-3-identity-linking.txt`
- Trace payload inspection: `genie/reports/evidence/discord-parity/phase-3-trace-inspection.txt`
- `user_external_ids` query: `genie/reports/evidence/discord-parity/phase-3-user-external-ids.txt`

## Residual Risks & Follow-ups
- Discord attachment/media parity is **not** validated; schedule follow-up testing for binary payloads.
- Real Discord integration (live bot) still pending; current manual scripts validate service behaviour without hitting the Discord API.

## Regression Checklist
- [x] Pytest suites GREEN
- [x] Discord mention + DM flows generate traces & payloads with shared `user_id`
- [x] `user_external_ids` populated via migration `7f3a2b1c9a01`
- [ ] Attachment/media flow parity (deferred)
- [ ] Live staging verification (deferred)

Keep this document updated with future evidence, additional scripts, or newly automated coverage.
