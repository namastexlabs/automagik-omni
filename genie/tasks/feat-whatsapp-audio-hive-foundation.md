# feat: whatsapp audio hive foundation

**Branch:** `feat/whatsapp-audio-hive-foundation`

[TASK]
Build the WhatsApp → Hive audio bridge that ingests Evolution webhook audio payloads, uploads them to Hive via multipart requests, and returns structured artifacts (audio bytes, audio URLs, or plain text) with no feature-flag gating.

[CONTEXT]
@src/channels/whatsapp/handlers.py - Incoming audio webhook parsing and dispatch hooks.  
@src/channels/whatsapp/audio_transcriber.py - Existing audio/base64 helpers to study for reuse.  
@src/services/automagik_hive_client.py - Hive client entry points for creating agent runs and parsing responses.  
@src/config.py - Remove any unused feature-flag wiring tied to WhatsApp audio Hive flow.

<task_breakdown>
1. [Discovery] Map how audio payloads arrive from Evolution and identify reusable helpers.  
2. [Implementation] Add temp-file extraction plus Hive multipart run helper that always executes, returns a structured response contract, and removes feature-flag gating.  
3. [Verification] Exercise helper via targeted unit tests or REPL to confirm MIME detection, cleanup, and contract outputs.
</task_breakdown>

[SUCCESS CRITERIA]
✅ Audio base64 converts to temp WAV/OGG with correct MIME inference.  
✅ Hive client method uploads audio via multipart and returns artifact descriptor (bytes or URL).  
✅ Response contract represents audio bytes, audio URLs, and plain text so callers can forward without extra branching.  
✅ Any existing `whatsapp_audio_to_hive_enabled` flag references are removed or no-ops.  
✅ Logging captures Hive errors and temp files are always cleaned up.

[NEVER DO]
❌ Reintroduce feature flags or optional gating for the Hive audio bridge.  
❌ Enable Hive streaming or modify unrelated Omni flows.  
❌ Leave temp files or secrets unresolved on disk.

## Concrete Examples
```python
with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=True) as tmp:
    tmp.write(base64.b64decode(evolution_payload.audio_base64))
    tmp.flush()
    mime = mimetypes.guess_type(tmp.name)[0] or "audio/wav"
    hive_result = hive_client.create_audio_run(file_path=tmp.name, mime_type=mime)
    return {
        "kind": hive_result.artifact_kind,
        "content": hive_result.payload,
        "mime_type": mime,
    }
```

## Technical Constraints
- Use Python tempfile utilities for secure cleanup.  
- Enforce explicit MIME detection before upload; fallback to WAV when uncertain.

<reasoning_config>
reasoning_effort: medium
verbosity: low_status_high_code
</reasoning_config>
