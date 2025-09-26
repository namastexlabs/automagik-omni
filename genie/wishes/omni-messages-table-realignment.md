# 🧞 Wish Template: Omni Messages Table Realignment

## 📋 Context & Objective

### 🎯 Primary Goal
Design and populate the Omni messages table using production-faithful webhook traces pulled via official APIs, replacing mock data with anonymized-but-realistic samples that mirror live payload structure across media types.

### 📊 Current Status
- **Progress**: Phase 0 – Discovery kickoff
- **Last Updated**: 2025-02-14 00:35
- **Assigned Agents**: GENIE (orchestration), automagik-omni-coder (pending), automagik-omni-qa-tester (pending)

### 🔍 Background Context
The existing `message_table_draft.csv` relies on synthetic values and lacks alignment with actual webhook fields stored in `message_traces`. We need to model the target Omni messages table after authentic payloads (including media, reactions, and metadata), ensuring anonymization without losing structural fidelity.

## 🧠 Shared Knowledge Base

### ✅ Discoveries
- FastAPI traces endpoint (`GET /api/v1/traces/{trace_id}`) supports retrieving trace payloads when authenticated via `x-api-key`.
- Adding `include_payload=true` to `/payloads` responses surfaces decompressed JSON, including nested `conversation`, `audioMessage`, and `reactionMessage` blocks plus compression metrics.
- Trace `0fe18991-5b6a-491d-b3e0-825feffa7707` anchors text/reference coverage; traces `488a36f8-0b03-4a7a-91f2-a72f6c15febc` (audio) and `18dacac4-e05c-46db-a4d8-fb004e0d546f` (document) reveal media-specific metadata fields (duration, hashes, waveform, file sizes).
- Reaction payload (`e7beef97-2c38-4c0e-b6d5-be4181dfb5a7`) demonstrates the need to infer message type from payload content because `message_traces.message_type` remains `unknown` for reactions.
- `/api/v1/instances` enumerates available channels (WhatsApp + Discord); Discord instance currently has no trace history, so future schema validation must remain channel-agnostic and document the missing sample coverage.

### 🚨 Issues Found
- Current CSV schema lacks compression metadata and message-stage coverage observed in real traces.
- Mock sample rows do not reflect Omni channel parity requirements (missing reaction/media variants and timestamps alignment).
- No Discord trace samples yet; need to confirm whether alternative environments can supply them or document the gap until data arrives.

### 💡 Solutions Applied
- Pending agent execution: use FastAPI `TestClient` to query traces and extract normalized payload structures for schema shaping.

### ❌ Approaches That Failed
- None yet; Omni MCP path flagged as unreliable for this effort, so direct API usage is mandated.

## 📂 Relevant Files
- `message_table_draft.csv`
- `src/api/app.py`
- `src/api/routes/traces.py`

## 🎯 Success Criteria
- Schema and sample rows mirror actual webhook payload shape, including media metadata, reactions, and compression markers.
- Field mapping aligns with `message_traces` records (ids, timestamps, media flags, compression sizes), with sensitive values anonymized but structurally intact.
- Validation evidence captured via API query transcripts and QA Death Testament confirming fidelity.

## 📝 Agent Updates Log

### 2025-02-14 00:00 - GENIE
Captured context, outlined phase plan (Discovery → Implementation → Validation), and prepared to delegate to coding and QA specialists upon approval.

---

**Template Usage**: 
1. Copy this template for new wishes
2. Reference with `@genie/wishes/[task-name].md` in agent prompts
3. Agents must read before starting work
4. Agents must update with all discoveries/progress

### 2025-02-14 00:35 - GENIE
- Queried running Omni API at `http://localhost:28882` with `x-api-key: namastex888` to pull production trace metadata.
- `GET /api/v1/traces/0fe18991-5b6a-491d-b3e0-825feffa7707` ➜ text message trace with compressed payloads; `include_payload=true` reveals `conversation` body and webhook envelope fields (`event`, `instance`, `messageTimestamp`).
- `GET /api/v1/traces/488a36f8-0b03-4a7a-91f2-a72f6c15febc/payloads?include_payload=true` ➜ audio payload shows media hashes, durations, waveform points, and size metadata (base64 + compression flags) critical for media columns.
- `GET /api/v1/traces/e7beef97-2c38-4c0e-b6d5-be4181dfb5a7/payloads?include_payload=true` ➜ reaction payload exposes `reactionMessage` structure; note `message_traces.message_type` currently `unknown` for reactions, so the new table must derive human-friendly enums from payload content.
- Catalogued additional trace ids via `/api/v1/traces?has_media=true&all_time=true` to ensure coverage for video, document, and other media types for schema mapping.
### 2025-02-14 00:38 - GENIE
- Confirmed Discord trace capture is currently broken (`/api/v1/traces?instance_name=genie-namastex-discord` ➜ empty set). Noted in scope that Phase 2 will implement WhatsApp-driven extraction first, with Discord parity deferred to a follow-up wish once the capture bug is resolved.
- Phase 2 deliverables for `automagik-omni-coder`:
  - Redefine `message_table_draft.csv` schema (LLM-friendly identifiers, participant metadata, content descriptors, media/compression fields, lifecycle timestamps).
  - Populate anonymized sample rows for text, image, audio, video, document, reaction, and agent error reply using traces `0fe18991-5b6a-491d-b3e0-825feffa7707`, `488a36f8-0b03-4a7a-91f2-a72f6c15febc`, `18dacac4-e05c-46db-a4d8-fb004e0d546f`, `1942749c-f6a2-4035-b6df-97c999a15d91`, `f94a3bc3-8a9a-49fb-a001-aeb9c9ba366c`, `e7beef97-2c38-4c0e-b6d5-be4181dfb5a7`.
  - Document column-to-trace mappings (top-of-file comments) and leave QA validation notes covering curl commands to rerun.
