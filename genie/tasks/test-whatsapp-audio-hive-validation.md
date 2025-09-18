# test: whatsapp audio hive validation

**Branch:** `test/whatsapp-audio-hive-validation`

[TASK]
Add automated coverage and documentation that validate the WhatsApp ↔ Hive audio flow, ensuring Omni forwards Hive responses (text, audio bytes, audio URLs) without feature-flag gating.

[CONTEXT]
@tests/test_whatsapp_audio_to_hive.py - New module for audio extraction and integration tests.  
@tests/test_automagik_hive_client.py - Existing Hive client tests to mirror request/response patterns.  
@src/channels/whatsapp/handlers.py - Reference integration points for constructing mocks.  
@docs/ - Add feature docs and operations notes per wish.  
@genie/wishes/whatsapp-audio-hive-wish.md - Validation scope and documentation expectations.

<task_breakdown>
1. [Discovery] Identify fixture patterns for Evolution webhooks and Hive responses.  
2. [Implementation] Create unit tests for audio extraction lifecycle and integration tests covering mocked Hive responses (plain text, bytes, URL) plus Evolution send shapes.  
3. [Verification] Update docs and run targeted `pytest` modules to prove coverage and behavior.
</task_breakdown>

[SUCCESS CRITERIA]
✅ Unit tests confirm audio base64 → temp file → cleanup path with MIME inference.  
✅ Integration tests mock Hive plain-text, bytes, and URL responses and assert WhatsApp sender payloads.  
✅ Documentation outlines the always-on bridge, Omni’s non-stream routing, and operational toggles (e.g., disabling Hive).  
✅ Test suite passes locally (targeted `pytest`) and in CI.

[NEVER DO]
❌ Rely on live Hive endpoints; use mocks/fixtures only.  
❌ Leave flaky tests or uncleaned temp files in test environments.  
❌ Suggest reinstating feature flags or manual gating around the Hive audio bridge.

## Concrete Examples
```python
def test_audio_payload_round_trip(tmp_path, hive_stub, evolution_sender):
    sample_audio = build_audio_payload(tmp_path)
    hive_stub.respond_with_audio_bytes(b"00ff", mime_type="audio/ogg")

    result = whatsapp_audio_hive_bridge.handle(sample_audio)

    assert result.kind == "audio_bytes"
    evolution_sender.sendWhatsAppAudio.assert_called_with(
        ANY,
        base64.b64encode(b"00ff").decode(),
        "audio/ogg",
    )
```

## Technical Constraints
- Prefer `tmp_path` fixtures for temporary files.  
- Keep docs concise; link to existing Hive references when possible.

<reasoning_config>
reasoning_effort: medium
verbosity: low_status_high_code
</reasoning_config>
