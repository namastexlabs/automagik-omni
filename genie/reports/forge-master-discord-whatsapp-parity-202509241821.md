# Forge Task Creation Report — Discord WhatsApp Parity
*Generated:* 2025-09-24 18:21 UTC
*Wish:* `genie/wishes/discord-whatsapp-parity.md`
*Wish Branch:* `wish/discord-whatsapp-parity`

## Human Decisions & Assumptions
- User approved forge plan on 2025-09-24 18:19 UTC.
- Assumed Group C owns `user_external_ids` migration work unless DBA guidance arrives later.
- Attachment payload scope set to metadata-first; escalate if raw storage becomes necessary.

## Created Tasks

### Group A — Parity Baseline Tests
- **Task ID:** `5c62b9ac-b4a1-4a45-b1f5-1c3631256374`
- **Title:** `test: discord parity baseline coverage`
- **Branch Guidance:** `test/discord-parity-baseline`
- **Complexity:** Medium (reasoning_effort: medium/think hard)
- **Dependencies:** None
- **Highlights:** Establish RED tests for Discord traces, payloads, and identity expectations.

### Group B — Discord Trace Persistence
- **Task ID:** `9cb141ed-b713-4567-95df-a16891cd2c2a`
- **Title:** `feat: discord trace persistence parity`
- **Branch Guidance:** `feat/discord-trace-persistence`
- **Complexity:** High (reasoning_effort: high/think harder)
- **Dependencies:** Group A (`5c62b9ac-b4a1-4a45-b1f5-1c3631256374`)
- **Highlights:** Implement inbound/outbound persistence, align router metadata, deliver evidence.

### Group C — Identity Linking Enablement
- **Task ID:** `989586df-4fcd-431c-909f-52806e30690c`
- **Title:** `feat: discord identity linking unification`
- **Branch Guidance:** `feat/discord-identity-linking`
- **Complexity:** High (reasoning_effort: high/think harder)
- **Dependencies:** Group A (`5c62b9ac-b4a1-4a45-b1f5-1c3631256374`), Group B (`9cb141ed-b713-4567-95df-a16891cd2c2a`)
- **Highlights:** Introduce shared identity helpers, migrations, and cross-channel user reuse.

### Group D — Validation & Runbook
- **Task ID:** `f3043b64-3783-450a-842c-152026cbea75`
- **Title:** `qa: discord parity validation runbook`
- **Branch Guidance:** `qa/discord-parity-validation`
- **Complexity:** Medium (reasoning_effort: medium/think hard)
- **Dependencies:** Group A (`5c62b9ac-b4a1-4a45-b1f5-1c3631256374`), Group B (`9cb141ed-b713-4567-95df-a16891cd2c2a`), Group C (`989586df-4fcd-431c-909f-52806e30690c`)
- **Highlights:** Execute QA flows, update docs, archive evidence.

## Next Actions for Agents
1. `automagik-omni-tests` to pull task `5c62b9ac-b4a1-4a45-b1f5-1c3631256374`, create RED coverage, and log failing pytest runs.
2. `automagik-omni-coder` to tackle trace persistence (`9cb141ed-b713-4567-95df-a16891cd2c2a`) once tests land, then proceed to identity linking (`989586df-4fcd-431c-909f-52806e30690c`).
3. `automagik-omni-qa-tester` to close out validation (`f3043b64-3783-450a-842c-152026cbea75`) with end-to-end evidence and doc updates after coding merges.

## Reporting & References
- Planning report: `@genie/reports/forge-plan-discord-whatsapp-parity-202509241815.md`
- Wish document: `@genie/wishes/discord-whatsapp-parity.md`
- Ensure each Death Testament references both this report and the planning report.

