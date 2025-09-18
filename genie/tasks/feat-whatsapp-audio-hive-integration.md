# feat: whatsapp audio hive integration

**Branch:** `feat/whatsapp-audio-hive-integration`

## Task Overview
Wire the WhatsApp audio handler to call the Hive audio pipeline, then deliver Hive-produced responses (text, audio bytes, or audio URLs) back to Evolution with no feature flag.

## Context & Background
@[src/channels/whatsapp/handlers.py] - Central message dispatcher where audio flow should branch.  
@[src/channels/whatsapp/evolution_api_sender.py] - Helpers for sending audio/media responses via Evolution.  
@[src/services/message_router.py] - Ensures routing contracts remain non-streaming.  
@[genie/wishes/whatsapp-audio-hive-wish.md] - Approved scope and response-forwarding expectations.

## Advanced Prompting Instructions
<context_gathering>
Understand existing audio send helpers and current text response path so Omni can forward Hive outputs without conditional gating.
</context_gathering>

<task_breakdown>
1. [Discovery] Identify handler entry point for audio messages and how responses are currently generated.  
2. [Implementation] Invoke foundation helper, branch on text vs audio artifacts, and send via the appropriate Evolution API sender.  
3. [Verification] Simulate Hive responses (text, bytes, URL) to ensure no streaming paths are activated and fallbacks behave gracefully when Hive fails.
</task_breakdown>

<success_criteria>
✅ Text responses from Hive follow the existing WhatsApp text reply path; audio bytes are base64-encoded with MIME before calling `sendWhatsAppAudio`; URLs use `sendMedia` with correct type.  
✅ Omni routing remains non-streaming and respects existing session contracts.  
✅ No feature-flag checks guard the new flow; legacy behavior degrades gracefully if Hive fails.  
✅ Errors surface with actionable logs while gracefully degrading to legacy behavior.
</success_criteria>

<never_do>
❌ Enable streaming or modify Omni streaming settings.  
❌ Break existing text or media handlers.  
❌ Reintroduce feature-flag gating around WhatsApp audio → Hive flow.
</never_do>

## Technical Constraints
- Must remain backward compatible for other message types while audio always routes through Hive.  
- Guard all Hive calls with robust exception handling to keep WhatsApp pipeline resilient.

## Reasoning Configuration
reasoning_effort: medium/think hard  
verbosity: low (status), high (code)
