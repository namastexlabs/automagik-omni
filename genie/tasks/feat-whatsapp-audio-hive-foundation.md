# feat: whatsapp audio hive foundation

**Branch:** `feat/whatsapp-audio-hive-foundation`

## Task Overview
Build the WhatsApp → Hive audio bridge that extracts Evolution webhook audio payloads, prepares multipart uploads, and returns Hive responses (audio bytes, audio URLs, or plain text) with no feature-flag gating.

## Context & Background
@[src/channels/whatsapp/handlers.py] - Incoming audio webhook parsing and dispatch hooks.  
@[src/channels/whatsapp/audio_transcriber.py] - Existing audio/base64 helpers to study for reuse.  
@[src/services/automagik_hive_client.py] - Hive client entry points for creating agent runs and parsing responses.  
@[src/config.py] - Remove any unused feature-flag wiring tied to WhatsApp audio Hive flow.

## Advanced Prompting Instructions
<context_gathering>
Start broad across WhatsApp audio helpers and Hive client, then narrow to functions handling media decoding and run creation.
</context_gathering>

<task_breakdown>
1. [Discovery] Map how audio payloads arrive from Evolution and identify reusable helpers.  
2. [Implementation] Add temp-file extraction + Hive multipart run helper that always executes and returns a structured response contract.  
3. [Cleanup] Remove legacy feature-flag code paths gating audio-to-Hive execution.  
4. [Verification] Exercise helper via targeted unit tests or REPL to confirm MIME detection, cleanup, and contract outputs.
</task_breakdown>

<success_criteria>
✅ Audio base64 converted to temp WAV/OGG with correct MIME inference.  
✅ Hive client method uploads audio via multipart and returns artifact descriptor (bytes or URL).  
✅ Response contract represents audio bytes, audio URLs, and plain text so callers can forward without extra branching.  
✅ Any existing `whatsapp_audio_to_hive_enabled` flag references are removed or no-ops.  
✅ Logging captures Hive errors and temp files are always cleaned up.
</success_criteria>

<never_do>
❌ Reintroduce feature flags or optional gating for the Hive audio bridge.  
❌ Enable Hive streaming or modify unrelated Omni flows.  
❌ Leave temp files or secrets unresolved on disk.
</never_do>

## Technical Constraints
- Use Python tempfile utilities for secure cleanup.  
- Enforce explicit MIME detection before upload; fallback to WAV when uncertain.

## Reasoning Configuration
reasoning_effort: medium/think hard  
verbosity: low (status), high (code)
