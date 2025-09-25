# Death Testament – Discord Trace Persistence Parity

## Scope
- Implemented Discord inbound trace creation aligned with WhatsApp semantics, including payload capture and trace lifecycle updates.
- Added outbound trace logging for Discord replies and omnichannel sender flows, ensuring parity with WhatsApp trace persistence.
- Introduced agent user caching for Discord to reuse agent-provided user identifiers across conversations.

## Files Touched
- `src/services/trace_service.py`
- `src/channels/discord/channel_handler.py`
- `src/channels/message_sender.py`

## Implementation Notes
- Extended `TraceService.create_trace` with channel-aware branching and Discord-specific trace construction while preserving WhatsApp behaviour.
- Added reusable outbound persistence helper `TraceService.record_outbound_message` for both handler responses and proactive sends.
- Enriched Discord handler with message serialization, trace lifecycle wiring, outbound logging, and agent user_id memoization.
- Wrapped omnichannel Discord sender calls with trace logging to capture proactive outbound payloads/failures.

## Evidence
- `uv run pytest tests/channels/test_discord_trace_parity.py`
  - Result: ✅ All 3 tests passed (Group A parity suite).

## Risks & Follow-ups
- Discord attachments currently logged as metadata only; media download/storage parity remains out of scope.
- Broader WhatsApp trace flows unaffected in unit scope; recommend Phase 2 validation with integrated WhatsApp regression suite before release.
- Consider augmenting `TraceService.record_outbound_message` to capture structured status codes once Discord IPC responses expose them.
