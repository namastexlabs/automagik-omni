# 🧞🐛 Debug Report - Credential Management Fix

## Issue Summary
The system was logging "API key mismatch" errors because the Gateway service was using a placeholder API key (`your-secret-api-key-here`) from the `.env` file, while the Python backend had auto-generated a secure key (`sk-omni-...`) in the SQLite database.

## Resolution Implemented
We transitioned the application to a true "Zero Config" state by prioritizing the database-stored key and ignoring invalid environment variables.

### Key Changes
1.  **Gateway (Node.js):**
    - Refactored `gateway/src/health.ts` to **ignore `.env`** for the API key.
    - Added logic to fetch the valid `omni_api_key` directly from the `data/automagik-omni.db` SQLite database using `sqlite3`.
    - This ensures the Gateway always uses the same key as the Backend.

2.  **Backend (Python):**
    - Updated `src/db/bootstrap_settings.py` to enforce a strict format for API keys. It now only accepts keys starting with `sk-omni-`.
    - This implicitly filters out the insecure placeholder `your-secret-api-key-here` without needing to hardcode it as a forbidden string.
    - Removed the explicit "blacklist" check from `src/api/deps.py`, simplifying the logic to trust the (now validated) configuration.

3.  **Cleanup:**
    - Removed references to the placeholder key from documentation and README files.

## Verification
- **Logs:** Confirmed that "API key mismatch" errors have stopped appearing in PM2 logs.
- **Health Check:** The Gateway is now successfully communicating with the Python backend using the database-sourced key.
- **Security:** The system no longer accepts or attempts to use the insecure placeholder key.

## Confidence Score: 100%
The root cause (config drift between file and DB) was identified and architecturally resolved by making the DB the single source of truth.
