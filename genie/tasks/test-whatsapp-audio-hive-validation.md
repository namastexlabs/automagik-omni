# test: whatsapp audio hive validation

**Branch:** `test/whatsapp-audio-hive-validation`

## Task Overview
Add automated coverage and documentation that validate the WhatsApp ↔ Hive audio flow, ensuring Omni forwards Hive responses (text, audio bytes, audio URLs) without feature-flag gating.

## Context & Background
@[tests/test_whatsapp_audio_to_hive.py] - New module for audio extraction and integration tests.  
@[tests/test_automagik_hive_client.py] - Existing Hive client tests to mirror request/response patterns.  
@[src/channels/whatsapp/handlers.py] - Reference integration points for constructing mocks.  
@[docs/] - Add feature docs and operations notes per wish.  
@[genie/wishes/whatsapp-audio-hive-wish.md] - Defines validation scope and documentation expectations.

## Advanced Prompting Instructions
<context_gathering>
Inspect existing WhatsApp/Hive tests to mirror fixtures and mocking utilities before writing new cases.
</context_gathering>

<task_breakdown>
1. [Discovery] Identify fixture patterns for Evolution webhooks and Hive responses.  
2. [Implementation] Create unit tests for audio extraction lifecycle and integration tests covering mocked Hive responses (plain text, bytes, URL) plus Evolution send shapes.  
3. [Documentation] Update docs/config to describe ASR+Answer+TTS flow, always-forward response behavior, and operational toggles.
</task_breakdown>

<success_criteria>
✅ Unit tests confirm audio base64 → temp file → cleanup path with MIME inference.  
✅ Integration tests mock Hive plain-text, bytes, and URL responses and assert WhatsApp sender payloads.  
✅ Documentation outlines the always-on bridge, Omni’s non-stream routing, and operational toggles (e.g., disabling Hive).  
✅ Test suite passes locally (`pytest` targeted modules) and in CI.
</success_criteria>

<never_do>
❌ Rely on live Hive endpoints; use mocks/fixtures only.  
❌ Leave flaky tests or uncleaned temp files in test environments.  
❌ Suggest reinstating feature flags or manual gating around the Hive audio bridge.
</never_do>

## Technical Constraints
- Prefer `tmp_path` fixtures for temporary files.  
- Keep docs concise; link to existing Hive references when possible.

## Reasoning Configuration
reasoning_effort: medium/think hard  
verbosity: low (status), high (code)
