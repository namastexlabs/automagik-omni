# Forge Plan — Discord WhatsApp Parity (2025-09-24 18:15 UTC)

## Discovery Summary
- Wish path: `genie/wishes/discord-whatsapp-parity.md` (status: DRAFT approved for execution).
- Goal: Mirror WhatsApp persistence patterns for Discord across users, traces, payloads, and identity linking with documentation + validation.
- Constraints: Red→Green→Refactor cadence, UV-only tooling, avoid altering WhatsApp semantics, capture evidence (tests, DB/log outputs, docs).

## Proposed Task Groups

### Group A — Parity Baseline Tests (agent: `automagik-omni-tests`)
- **Scope:** Analyze WhatsApp coverage, craft failing tests covering Discord inbound/outbound trace persistence, identity linking expectations, and logging metadata.
- **Dependencies:** None (kicks off RED phase).
- **Evidence:** Death Testament, pytest output (`uv run pytest` selections), notes on WhatsApp reference cases.

### Group B — Discord Trace Persistence (agent: `automagik-omni-coder`)
- **Scope:** Implement inbound + outbound trace writers, payload persistence, router metadata alignment, logging fields mirroring WhatsApp.
- **Dependencies:** Requires Group A tests as guardrails.
- **Evidence:** Passing Group A tests, additional unit coverage if introduced, DB/log verification snippets, Death Testament.

### Group C — Identity Linking Enablement (agent: `automagik-omni-coder`)
- **Scope:** Introduce/extend `user_external_ids`, ensure Discord + WhatsApp lookup helpers share logic, wire creation/upsert flows, adjust session naming.
- **Dependencies:** Depends on Group B foundations (shared helpers) and leverages Group A tests.
- **Evidence:** Migration diff preview, service/unit tests, trace samples showing shared user IDs, Death Testament.

### Group D — Validation & Runbook (agent: `automagik-omni-qa-tester`)
- **Scope:** Execute end-to-end validation (guild mention, DM), compile operational checklist, update docs/runbook per wish requirements, ensure evidence archived.
- **Dependencies:** Requires Groups B & C completed.
- **Evidence:** QA walkthrough logs, documentation diffs, Death Testament referencing prior groups' outputs.

## Outstanding Questions for Humans
1. Confirm that migration ownership for `user_external_ids` sits with Group C (and no separate DBA sign-off needed).
2. Clarify desired depth for Discord attachment payload storage (metadata-only vs raw payload preservation).

## Approval Block
- **Decision:** _Pending human approval_
- **Notes:** Once approved, forge tasks will be created sequentially (Group A → D respecting dependencies).

