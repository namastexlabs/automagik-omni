# 🧞 Omni Action Queue WISH

**Status:** DRAFT
**Parent Wish:** @genie/wishes/omni-event-fabric-and-action-engine.md
**Dependency:** @genie/wishes/omni-event-fabric-foundation-wish.md (must complete first)

## Executive Summary
Build a robust asynchronous action processing system for Omni events, enabling reliable webhook handling, retry logic, and scalable action execution without blocking the ingestion pipeline.

## Current State Analysis
- **What exists:** Synchronous processing in channel handlers; no retry mechanism; failures block ingestion
- **Gap identified:** No queue infrastructure, no worker processes, no dead letter handling
- **Solution approach:** Introduce lightweight queue (Redis/BullMQ or SQLite-based), worker pool, retry logic, monitoring

## Success Criteria
✅ Incoming events queued for async processing without blocking webhook responses
✅ Worker processes execute actions with configurable concurrency
✅ Failed actions retry with exponential backoff
✅ Dead letter queue captures persistently failing events
✅ Queue metrics exposed for monitoring (depth, throughput, failure rate)

## Technical Architecture
Events flow: webhook → omni_events (sync) → queue → workers → action execution
Queue options evaluation:
- **Option A: Redis + BullMQ** - Battle-tested, UI dashboard, complex setup
- **Option B: SQLite + Celery** - Simple deployment, uses existing DB, less scalable
- **Option C: PostgreSQL LISTEN/NOTIFY** - Native if we migrate from SQLite
- **Decision Required:** Balance simplicity vs scalability for local-first deployment

## Task Decomposition
- **Group Name:** queue-infrastructure
  - **Goal:** Set up chosen queue system with workers
  - **Creates/Modifies:** Queue tables/Redis setup, worker processes, configuration
  - **Dependencies:** Foundation wish complete, queue technology chosen

- **Group Name:** action-registry
  - **Goal:** Define action types, handlers, and routing
  - **Creates/Modifies:** Action handler classes, registry pattern, configuration schema
  - **Dependencies:** Queue infrastructure ready

- **Group Name:** retry-resilience
  - **Goal:** Implement retry logic, dead letter queue, monitoring
  - **Creates/Modifies:** Retry policies, DLQ handling, metrics endpoints
  - **Dependencies:** Action registry complete

## Open Questions & Clearance Log

| Item | Owner | Status | Evidence | Impact |
| --- | --- | --- | --- | --- |
| Queue technology choice (Redis vs SQLite vs other) | Human | Open | — | Architecture blocker |
| Worker deployment model (threads vs processes vs containers) | Human | Open | — | Infrastructure blocker |
| Action configuration format (YAML vs Python vs DB) | Human | Open | — | API design blocker |

## Status Log
- 2025-09-26 – Created as split from foundation wish per human decision to separate queue complexity