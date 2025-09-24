# Automagik Omni QA Tester • Death Testament

Title: qa: discord parity validation evidence
Slug: discord-parity-validation
When (UTC): 2025-09-24 20:42:54
Branch: qa/discord-parity-validation

## Scope
- Validate Discord ↔ WhatsApp parity after Groups A–C implementations.
- Confirm regression suites, trace persistence, and identity linking behave identically across guild mention and DM scenarios.
- Document reproducible steps and artefacts for merge readiness assessment.

## Environment
- Repo: automagik-omni (hot VM with staged `.env`).
- Database: `automagik.db` (migrated to Alembic revision 7f3a2b1c9a01 for `user_external_ids`).
- Evidence directory: `genie/reports/evidence/discord-parity/`.

## Automated Validation
| Command | Result | Evidence |
| --- | --- | --- |
| `uv run pytest tests/channels/test_discord_trace_parity.py` | ✅ 3 passed | `genie/reports/evidence/discord-parity/phase-2-pytest-discord-trace.txt` |
| `uv run pytest tests/test_omni_handlers.py::TestDiscordChatHandler` | ✅ 8 passed | `genie/reports/evidence/discord-parity/phase-2-pytest-omni-handlers.txt` |
| `uv run pytest tests/test_identity_linking.py` | ✅ 3 passed | `genie/reports/evidence/discord-parity/phase-2-pytest-identity-linking.txt` |
| `uv run pytest tests/channels/discord/test_channel_handler.py` | ✅ 2 passed | `genie/reports/evidence/discord-parity/phase-2-pytest-channel-handler.txt` |
| `uv run pytest tests/channels/test_message_sender.py` | ✅ 2 passed | `genie/reports/evidence/discord-parity/phase-2-pytest-message-sender.txt` |

## Manual Validation
- Simulated guild mention and DM flows via stubbed Discord objects invoking `DiscordChannelHandler._handle_message` twice to exercise real trace logging. Output: `genie/reports/evidence/discord-parity/phase-3-manual-flow.txt`.
- Created WhatsApp user, linked Discord external ID, and reran flows to validate cached `user_id` reuse. Output: `genie/reports/evidence/discord-parity/phase-3-identity-linking.txt`.
- Queried `message_traces`/`trace_payloads` for new entries (guild + DM) showing inbound/outbound parity and metadata alignment. Output: `genie/reports/evidence/discord-parity/phase-3-trace-inspection.txt`.
- Verified `user_external_ids` contains the Discord → Automagik mapping. Output: `genie/reports/evidence/discord-parity/phase-3-user-external-ids.txt`.

## Key Findings
- ✅ Trace persistence parity confirmed: inbound `webhook_received` payloads capture Discord metadata and outbound `discord_send` stages mirror WhatsApp logging semantics.
- ✅ Identity linking works after applying migration `7f3a2b1c9a01`; Discord external ID resolves to the WhatsApp-seeded user (`9946478a-f8da-4514-a46b-5f68faca6086`).
- ✅ pytest suites for parity, handler contracts, identity helpers, and the new Discord sender/handler edge cases are GREEN.
- ⚠️ Required migration was not applied in local DB prior to QA; running `uv run alembic upgrade 7f3a2b1c9a01` is mandatory before validation.
- ⚠️ Manual flows rely on monkeypatched `message_router` to avoid live agent calls; live Discord bot testing remains outstanding.
- ⚠️ No coverage yet for Discord media/attachment payloads.

## Risks & Follow-ups
1. **Media parity gap** — Need follow-up wish to exercise attachments/files through trace pipeline.
2. **Live Discord integration** — Validate against staging bot with real API tokens to ensure actual round-trip behaviour.
3. **Test suite maintenance** — Keep the new Discord handler/sender suites in sync with future feature updates.
4. **Migration enforcement** — Incorporate migration check into setup scripts so QA cannot run against stale schemas.

## Evidence Index
- Automated transcripts: `genie/reports/evidence/discord-parity/phase-2-*.txt`
- Manual flow outputs: `genie/reports/evidence/discord-parity/phase-3-manual-flow.txt`
- Identity link confirmation: `genie/reports/evidence/discord-parity/phase-3-identity-linking.txt`
- Trace payload inspection: `genie/reports/evidence/discord-parity/phase-3-trace-inspection.txt`
- External ID query: `genie/reports/evidence/discord-parity/phase-3-user-external-ids.txt`
- Runbook: `docs/discord-parity-validation.md`

## Summary for Humans
Discord parity behaves as expected for text-based guild mentions and DMs once the identity migration is applied. All automated suites are green, traces/payloads show consistent metadata, and Discord IDs resolve to the WhatsApp-seeded user. Remaining blockers are media coverage, live environment confirmation, and scripting guardrails for schema migrations.
