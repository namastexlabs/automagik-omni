# 🧞 WhatsApp Audio Hive WISH

**Status:** APPROVED

## Executive Summary
Enable WhatsApp audio messages to be processed end-to-end through Hive for ASR, answer generation, and TTS, then return synthesized audio back to WhatsApp.

## Current State Analysis
**What exists:** WhatsApp handlers manage text workflows; Hive integrations exist for text-based agent runs; no audio extraction/upload pipeline.  
**Gap identified:** Audio messages are not transformed into Hive-compatible files, nor are Hive audio artifacts routed back to WhatsApp.  
**Solution approach:** Build an always-on audio bridge that extracts WhatsApp audio, posts it to Hive as a multipart run, retrieves Hive responses (audio bytes, audio URLs, or plain text), and forwards them through existing Evolution senders with robust validation and docs.

## Fork Compatibility Strategy
- **Isolation principle:** Keep changes scoped to WhatsApp audio handling and the Hive client so default text flows remain untouched.  
- **Extension pattern:** Reuse existing WhatsApp handler hooks and Hive client abstractions without modifying unrelated channel logic.  
- **Merge safety:** Contain edits to WhatsApp audio handling, Hive client helpers, and docs/tests so upstream merges remain conflict-light.

## Success Criteria
✅ WhatsApp audio converted to temp WAV/OGG files with correct MIME detection.  
✅ Hive `/playground/agents/{agent_id}/runs` invoked via multipart upload and returns audio artifact reference.  
✅ WhatsApp handler relays Hive-produced responses (audio bytes, audio URLs, or plain text) directly through Evolution senders.  
✅ Automated tests cover audio extraction lifecycle and mocked Hive round-trip; documentation explains response handling behaviors.

## Never Do (Protection Boundaries)
❌ Modify text-only WhatsApp routing paths or enable streaming in Omni.  
❌ Introduce unchecked audio streaming outside Hive's standard response handling.  
❌ Diverge from the principle that Omni forwards Hive responses exactly as returned (text stays text, audio stays audio).

## Technical Architecture

### Component Structure
Backend (Python):
- `src/channels/whatsapp/handlers.py` – invoke audio pipeline for incoming audio and forward Hive responses.
- `src/services/hive_client.py` (or equivalent) – add multipart audio run helper.
- `src/services/audio_processing/` (new or existing) – manage base64 decoding, MIME inference, temp file lifecycle.
- `src/channels/evolution_api_sender.py` – ensure audio send helper handles Hive response payloads (bytes or URLs) and plain text passthrough.

Support:
- `tests/channels/whatsapp/test_audio_to_hive.py` – unit/integration coverage.  
- `docs/features/whatsapp-audio-hive.md` – configuration + ops notes.

### Naming Conventions
- Temp audio files: `wa-audio-<uuid>.{ext}` stored via `tempfile`.  
- Branches: `feat/whatsapp-audio-hive-foundation`, `feat/whatsapp-audio-hive-integration`, `test/whatsapp-audio-hive-validation`.

## Task Decomposition

### Dependency Graph
```
A[Foundation] ──► B[Integration] ──► C[Validation]
```

### Group A (Foundation) – Branch `feat/whatsapp-audio-hive-foundation`
- Extract base64 audio from Evolution webhook payloads, detect MIME, and persist as temp WAV/OGG.  
- Implement Hive multipart upload (`message`, `stream=false`, `monitor=false`, `session_id`, `user_id`, audio file field).  
- Parse Hive response and expose response contract that can represent audio bytes, audio URLs, or plain text.  
- Remove any existing feature-flag gating so downstream callers can rely on the new pipeline unconditionally.

### Group B (Integration) – Branch `feat/whatsapp-audio-hive-integration`
- Update WhatsApp handler to call Group A pipeline for all audio messages.  
- Deliver Hive responses: send text replies via existing text path; use `evolution_api_sender.sendWhatsAppAudio` (bytes→base64 + MIME) for byte artifacts; use `sendMedia` (URL + mimetype) when Hive returns a URL.  
- Ensure Omni never enables streaming for this flow and relies on standard routing while removing any obsolete flag checks.

### Group C (Validation) – Branch `test/whatsapp-audio-hive-validation`
- Add unit tests for audio extraction, MIME inference, and temp file cleanup.  
- Add integration tests mocking Hive responses (plain text, bytes, and URL variants) validating Evolution send payloads.  
- Document ASR+Answer+TTS pipeline, the always-forward response contract, and operational guidance.

## Execution Notes
- Maintain backward compatibility: text and other media handling must continue as today while audio routes through Hive.  
- Centralize temp file cleanup via context manager to avoid leaks.  
- Capture Hive errors with clear logging to aid future observability work and define graceful fallback if Hive fails.

## Definition of Done
- Audio messages round-trip via Hive successfully in staging, and their responses are forwarded verbatim (text or audio).  
- Hive failures degrade gracefully with clear logs and fallback behavior.  
- Tests green locally and in CI for new coverage.  
- Docs updated so ops understands the always-on bridge and response handling.
