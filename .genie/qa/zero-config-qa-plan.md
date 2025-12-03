# QA Plan: Zero Config Architecture Transition

**Version:** 1.0
**Date:** December 3, 2025
**Objective:** Validate the removal of `.env` dependencies and the successful implementation of the database-driven "Zero Config" API key management system.

## 1. Scope
*   **In Scope:**
    *   API Key generation and storage in SQLite (`omni_global_settings`).
    *   Backend (Python) authentication logic (`src/api/deps.py`).
    *   Gateway (Node.js) authentication for health checks (`gateway/src/health.ts`).
    *   System startup and bootstrapping (`src/db/bootstrap_settings.py`).
    *   Persistence of configuration across restarts.
*   **Out of Scope:**
    *   Evolution API internal logic (except its connection to Omni).
    *   Discord bot specific functionality (unless related to auth).
    *   UI visual regression (focus is on API/Auth).

## 2. Test Environment
*   **OS:** Linux (Production/Staging)
*   **Database:** SQLite (`data/automagik-omni.db`)
*   **Services:**
    *   `automagik-omni` (Gateway + Python Backend) running via PM2.
*   **Pre-conditions:**
    *   No `.env` files exist in the project root or subdirectories.
    *   No "your-secret-api-key-here" string exists in the codebase.

## 3. Test Cases

| ID | Test Scenario | Steps | Expected Result |
| :--- | :--- | :--- | :--- |
| **TC-01** | **Fresh Install Bootstrap** | 1. Stop services.<br>2. Delete `data/automagik-omni.db`.<br>3. Start services. | 1. Services start without error.<br>2. Log shows "Auto-generated Omni API key".<br>3. Key in DB starts with `sk-omni-`. |
| **TC-02** | **Gateway Health Auth** | 1. Wait for boot.<br>2. Request `GET http://localhost:8882/health`. | 1. Response status 200 OK.<br>2. JSON body shows `services.python.status` as "up".<br>3. No 401 errors in Python logs. |
| **TC-03** | **Valid Client Auth** | 1. Retrieve key from DB: `SELECT value FROM omni_global_settings WHERE key='omni_api_key'`.<br>2. Request `GET /api/v1/instances` with `x-api-key: <key>`. | 1. Response status 200 OK.<br>2. Returns list of instances (empty list is fine). |
| **TC-04** | **Invalid Client Auth** | 1. Request `GET /api/v1/instances` with `x-api-key: invalid-key`. | 1. Response status 401 Unauthorized. |
| **TC-05** | **Persistence Check** | 1. Restart services (`pm2 restart`).<br>2. Check logs. | 1. Log shows "Omni API key already exists".<br>2. Key value remains unchanged from TC-01. |
| **TC-06** | **Key Validation (Format)** | 1. Stop services.<br>2. Manually update DB key to "bad-format-key".<br>3. Start services. | 1. System detects invalid format.<br>2. Regenerates a new `sk-omni-` key.<br>3. Overwrites the bad key in DB. |
| **TC-07** | **Env File Isolation** | 1. Create a dummy `.env` with `AUTOMAGIK_OMNI_API_KEY=fail`.<br>2. Restart services.<br>3. Check active key. | 1. System IGNORES the `.env` file.<br>2. Active key is still the DB key.<br>3. Client auth works with DB key, fails with "fail". |

## 4. Execution Strategy
Tests will be executed sequentially using CLI tools (`curl`, `sqlite3`, `pm2`). Logs will be inspected for specific patterns.

## 5. Defect Tracking
Any deviations will be logged as critical blockers, given the security implications of auth failures.

## 6. Deliverables
*   This QA Plan.
*   Execution Log (Terminal output).
*   Final Sign-off Report.
