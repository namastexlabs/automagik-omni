# 🧞 Multimodal Minimal PR Restructure WISH

**Status:** DRAFT

## Executive Summary
Restructure recent multimodality experiments (media, voice, Hive streaming) into a minimal, standards-aligned implementation with the smallest viable change set, reusing successful parts, pruning dead code, and preparing a clean PR branch.

## Current State Analysis
**What exists:**
- Omni endpoints at `src/api/routes/omni.py` with `OmniChannelInfo.supports_media` and `supports_voice`.
- Unified send endpoints in `src/api/routes/messages.py` for text/media/audio with normalized payloads.
- WhatsApp media handling including `media_contents` propagation and decryption util; audio transcription service present but disabled.
- Discord voice scaffolding in `src/channels/discord/voice_manager.py`, flag controls in `src/commands/discord_service_manager.py`; STT placeholder, TTS optional.
- Hive client with streaming support and robust chunk parsing in `src/services/automagik_hive_client.py`; routing logic in `src/services/message_router.py` selecting streaming vs non-streaming.
- Experimental streaming handler for WhatsApp at `src/channels/whatsapp/streaming_handler.py` not yet integrated with the active WhatsApp handler.

**Gap identified:**
- Inconsistent integration of streaming path in WhatsApp handler; decorator-based integration not applied.
- Capability flags may not reflect actual per-instance readiness (e.g., voice for Discord depends on token + enable flag).
- Experimental files and dead code likely present from prior iterations; risk of drift from project standards.
- Audio transcription path is present but disabled; current stance needs to be explicit in docs and API behavior.

**Solution approach:**
- Minimal, additive edits focusing on: (1) accurate capability flags, (2) stable media payload contract, (3) non-invasive streaming routing, (4) guardrails for Discord voice, (5) cleanup of experimental dead code deferred to follow-up PR if risky.

## Fork Compatibility Strategy
- **Isolation principle:** Keep experimental helpers in channel-specific modules; avoid core API shape changes; do not rename existing files.
- **Extension pattern:** Add capability checks and small conditionals rather than large refactors; integrate streaming via existing `message_router.route_message_smart` calls, not decorators.
- **Merge safety:** Limit churn to a handful of files; remove only clearly unused experimental files with zero references; otherwise mark for follow-up cleanup PR.

## Success Criteria
✅ `OmniChannelInfo.supports_voice` and `supports_media` accurately reflect instance capabilities
✅ WhatsApp and Discord media flows pass `media_contents` end-to-end without server-side STT
✅ WhatsApp streaming path can be enabled via instance config; falls back cleanly when disabled
✅ Discord voice features are gated by config; no crashes when libs missing
✅ Tests cover capability flags, streaming decision matrix, and media payload propagation
✅ Dead obvious experimental files pruned or listed for follow-up removal

## Never Do (Protection Boundaries)
❌ Large-scale handler rewrites or file renames
❌ Enabling server-side STT by default
❌ Changing public API schemas or routes
❌ Introducing hard dependencies on optional voice libraries at import time

## Technical Architecture

### Component Structure
Backend only:
- `src/api/routes/omni.py` — ensure capability flags reflect instance config (Discord voice only when truly available)
- `src/api/routes/messages.py` — keep audio forwarded as media; validate schemas
- `src/services/message_router.py` — authoritative streaming decision and routing (smart path)
- `src/channels/whatsapp/handlers.py` — call router smart path directly where appropriate; no decorator coupling
- `src/channels/discord/voice_manager.py` — keep provider injection points; no-op STT by default

### Naming Conventions
- Services, handlers, and routes retain existing names
- No new top-level modules unless essential; prefer small, local edits

## Task Decomposition

### Dependency Graph
```
A[Foundation] ──► B[Core Logic] ──► C[API Surface] ──► D[Tests] ──► E[Docs]
           └─────────────────────────────────────────────────► F[Cleanup]
```

### Group A: Foundation (Parallel)
- A1-capabilities: Compute `supports_voice` per-instance
  - Context: `@src/api/schemas/omni.py`, `@src/commands/discord_service_manager.py`, `@src/db/models.py`
  - Modifies: `get_channel_info` implementations in channel handlers, ensuring `supports_voice=True` only if Discord token present and `discord_voice_enabled` true; WhatsApp voice remains False (no server STT)
  - Success: Omni channels endpoint reflects real capabilities

- A2-media-contract: Confirm and document `media_contents` shape
  - Context: `@src/services/message_router.py`, `@src/services/agent_api_client.py`, `@src/services/agent_api_client_async.py`, `@src/channels/whatsapp/handlers.py`
  - Modifies: Comments/docstrings and minimal validation to ensure payload passes unchanged; no schema changes
  - Success: Media e2e tests observe identical structure through layers

- A3-streaming-switch: Centralize streaming decision via router
  - Context: `@src/services/message_router.py`
  - Modifies: None or minimal; keep logic authoritative; expose helper for WhatsApp handler call
  - Success: Single source of truth for streaming vs non-streaming

### Group B: Core Logic (After A)
- B1-whatsapp-routing: Integrate smart routing in active handler
  - Context: `@src/channels/whatsapp/handlers.py`
  - Modifies: In message processing path, when instance is hive-stream-enabled, call `message_router.route_message_smart(...)`; else existing flow
  - Success: Streaming can be toggled per-instance without decorators

- B2-discord-voice-guardrails: Harden config checks
  - Context: `@src/commands/discord_service_manager.py`, `@src/channels/discord/bot_manager.py`
  - Modifies: Ensure voice paths respect global flag and instance `discord_voice_enabled`; avoid imports when disabled
  - Success: No voice operations invoked when disabled; app starts without optional deps

- B3-audio-forwarding: Clarify WhatsApp audio behavior
  - Context: `@src/channels/whatsapp/audio_transcriber.py`, `@src/channels/whatsapp/handlers.py`
  - Modifies: Keep transcription service disabled; ensure audio messages are marked `message_type="voice"` and forwarded as media to agents
  - Success: Consistent behavior; no surprise server STT

### Group C: API Surface (After B)
- C1-omni-endpoints: Ensure capability flags and errors are consistent
  - Context: `@src/api/routes/omni.py`
  - Modifies: Minor adjustments to capability population via handlers
  - Success: Accurate capabilities for UI/consumers

- C2-message-endpoints: Validate audio/media inputs
  - Context: `@src/api/routes/messages.py`
  - Modifies: Add clear errors when neither URL nor base64 provided; explicit note that audio is forwarded
  - Success: Predictable API usage and docs

### Group D: Testing & Validation (After C)
- D1-unit: Capability flags matrix
  - Creates/Modifies: tests to validate `supports_voice` and media contract
- D2-integration: Streaming decision and payload propagation
  - Modifies: existing tests `@tests/test_omni_endpoints.py`, `@tests/test_comprehensive_integration.py`, add focused cases for hive streaming and media
- D3-e2e: WhatsApp webhook with audio/media
  - Ensures: agent clients receive `media_contents` and correct `message_type`

### Group E: Docs (After D)
- E1-CLAUDE/wish-doc: Explicitly state audio is forwarded; Discord voice scaffold off by default; streaming toggle per-instance
- E2-API docs: Brief notes in OpenAPI descriptions where appropriate

### Group F: Cleanup (Parallel, low-risk; else follow-up PR)
- F1-identify-deadcode: Locate experimental files with no references
  - Tools: rg search for references; candidates include unused streaming decorators/helpers
  - Action: If zero references and trivial, delete; else list for follow-up PR
- F2-test-artifacts: Remove stray test/docs files unrelated to final plan

## Implementation Examples
- Use `message_router.route_message_smart` for WhatsApp when `agent_stream_mode` true and hive configured
- Keep `BasicSTTProvider` returning empty string; document STT provider injection point for future

## Testing Protocol
```bash
# API
pytest -q tests/test_omni_endpoints.py::test_omni_channels_capabilities
pytest -q tests/test_comprehensive_integration.py::test_streaming_routing_decision

# Media propagation
pytest -q tests/test_omni_handlers.py::test_media_contents_propagation
```

## Validation Checklist
- [ ] No file renames; minimal edits only
- [ ] Capability flags accurate per-instance
- [ ] Streaming toggle works and falls back cleanly
- [ ] Media payloads unchanged through layers
- [ ] Voice disabled flows do not import optional deps
- [ ] No server-side STT enabled by default
- [ ] Dead code either removed (no refs) or listed for follow-up

## Status Lifecycle
- DRAFT → READY_FOR_REVIEW after tests updated/passing

## 📦 Branching & PR Strategy
- Create a fresh feature branch from `origin/main`: `feat/multimodal-minimal-pr`
- Cherry-pick or absorb working experimental edits already on `feat/multimodal-hive-0c17` where applicable, but keep diff minimal
- Separate follow-up PR for risky/deletions if necessary

## Questions for clarification
1. Should we keep server-side STT fully disabled and forward audio to agents only?
2. For Discord voice, keep scaffold but off by default in this PR?
