# Automagik Omni Tests Death Testament

## Scope
- Wish: Discord ↔ WhatsApp parity baseline (trace persistence, payload storage, identity linking).
- Branch: `test/discord-parity-baseline`.
- Files: `tests/channels/test_discord_trace_parity.py` (new RED coverage).

## Tests Authored
1. `test_discord_inbound_creates_trace_payload` — expects inbound Discord flow to create a `TraceService` record and log the raw payload (`webhook_received`) similar to WhatsApp webhook handling.
2. `test_discord_outbound_writes_trace_payload` — asserts outbound Discord sends persist a trace + payload record (mirroring WhatsApp’s `log_evolution_send`).
3. `test_discord_identity_links_agent_user_id` — verifies Discord messages reuse the agent `user_id` returned from the first interaction so cross-channel identity remains stable.

## Execution Evidence
- Command: `uv run pytest tests/channels/test_discord_trace_parity.py`
- Result: **FAIL (expected RED)**
  - Inbound parity failure: `TraceService.create_trace` never called (0 invocations).
  - Outbound parity failure: `TraceService.record_outbound_message` never called (0 invocations).
  - Identity linking failure: second Discord message still routes with `user_id=None` instead of the stored `agent-user-123`.

## Reference Notes
- WhatsApp parity anchors: `src/channels/whatsapp/handlers.py` uses `user_service.get_or_create_user_by_phone`, reuses `last_agent_user_id`, and logs payloads via `trace_context.log_stage` / `log_evolution_send`.
- Discord gaps surfaced: `src/channels/discord/channel_handler.py` and `src/channels/message_sender.py` omit trace orchestration and identity reuse entirely.

## Follow-up Recommendations
1. Introduce Discord-aware trace wiring (create + stage logging) in inbound handler and outbound sender.
2. Extend identity services/models to map `discord_user_id` (and guild scope) to a stable Automagik user record; reuse `agent_user_id` on subsequent messages.
3. Backfill database schema / services to persist payload bodies for Discord events (parallel to WhatsApp’s `trace_payloads`).

## Human Revalidation Steps
1. Implement Discord trace + identity propagation features.
2. Re-run `uv run pytest tests/channels/test_discord_trace_parity.py` and ensure all three cases go GREEN.
3. Expand regression matrix to cover Discord webhook endpoints once core parity passes.

