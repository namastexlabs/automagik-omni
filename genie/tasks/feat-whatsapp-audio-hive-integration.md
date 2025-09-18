# feat: whatsapp audio hive integration

**Branch:** `feat/whatsapp-audio-hive-integration`

[TASK]
Wire the WhatsApp audio handler to call the Hive audio pipeline and deliver Hive-produced responses (text, audio bytes, or audio URLs) back to Evolution with no feature flag gating.

[CONTEXT]
@src/channels/whatsapp/handlers.py - Central message dispatcher where audio flow should branch.  
@src/channels/whatsapp/evolution_api_sender.py - Helpers for sending audio/media responses via Evolution.  
@src/services/message_router.py - Ensures routing contracts remain non-streaming.  
@genie/wishes/whatsapp-audio-hive-wish.md - Approved scope and response-forwarding expectations.

<task_breakdown>
1. [Discovery] Identify handler entry point for audio messages and how responses are currently generated.  
2. [Implementation] Invoke the foundation helper, branch on text vs audio artifacts, and send via the appropriate Evolution API sender.  
3. [Verification] Simulate Hive responses (text, bytes, URL) to ensure no streaming paths activate and fallbacks behave gracefully when Hive fails.
</task_breakdown>

[SUCCESS CRITERIA]
✅ Text responses from Hive follow the existing WhatsApp text reply path.  
✅ Audio bytes are base64-encoded with MIME metadata before calling `sendWhatsAppAudio`.  
✅ URLs use `sendMedia` with the correct media type while session routing stays non-streaming.  
✅ No feature-flag checks guard the flow; failures fall back to the legacy response path with actionable logs.

[NEVER DO]
❌ Enable streaming or modify Omni streaming settings.  
❌ Break existing text or media handlers.  
❌ Reintroduce feature-flag gating around the WhatsApp audio → Hive flow.

## Concrete Examples
```python
hive_result = whatsapp_audio_hive_bridge.run(payload)
if hive_result.kind == "text":
    send_text(session, hive_result.content)
elif hive_result.kind == "audio_bytes":
    encoded = base64.b64encode(hive_result.content).decode()
    evolution_api_sender.sendWhatsAppAudio(session, encoded, hive_result.mime_type)
elif hive_result.kind == "audio_url":
    evolution_api_sender.sendMedia(session, hive_result.content, media_type="audio")
else:
    logger.warning("Unknown Hive artifact", extra={"artifact": hive_result})
    send_fallback_text(session)
```

## Technical Constraints
- Must remain backward compatible for other message types while audio always routes through Hive.  
- Guard all Hive calls with robust exception handling to keep the WhatsApp pipeline resilient.

<reasoning_config>
reasoning_effort: medium
verbosity: low_status_high_code
</reasoning_config>
