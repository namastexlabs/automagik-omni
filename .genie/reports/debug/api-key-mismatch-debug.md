## Top 3 Hypotheses (Evidence-Based)

### 🥇 Hypothesis 1: Gateway Health Checker Uses Placeholder Key (Confidence: 95%)
**Root Cause:** The `HealthChecker` in `gateway/src/health.ts` reads `AUTOMAGIK_OMNI_API_KEY` from `.env`. Since the user has the default `.env`, this value is `"your-secret-api-key-here"`. The Health Checker uses this key to call `/api/v1/instances` to enrich health data. The Python backend correctly rejects this placeholder key, causing the 401 errors and "API key mismatch" logs.
**Evidence:**
- **Log Match:** The log "API key mismatch. Got: [your****************here]" exactly matches the placeholder in `.env`.
- **Source Code:** `gateway/src/health.ts` L120 explicitly sends `'x-api-key': this.omniApiKey`.
- **Timing:** The errors occur periodically, consistent with health check polling.
- **Network:** Requests originate from `127.0.0.1` (Gateway talking to Python).
**Location:** `gateway/src/health.ts:116-125` (inside `getOmniInstanceKeys`)
**Fix Approach:** Modify `gateway/src/health.ts` to check if `this.omniApiKey` is the placeholder. If it is, skip the `/api/v1/instances` call to prevent the error.
**Regression Check:** Restart gateway and observe logs. The "API key mismatch" errors should stop.

### 🥈 Hypothesis 2: UI LocalStorage Persistence (Confidence: 20%)
**Root Cause:** The frontend might have stored the placeholder key in `localStorage` during an earlier session.
**Evidence:**
- **Weakness:** The logs show requests coming from `127.0.0.1`. While a browser *could* be running locally (e.g., via RDP), the Gateway hypothesis explains the behavior more directly and matches the code logic perfectly.
**Location:** Browser `localStorage`.
**Fix Approach:** Clear browser data.
**Regression Check:** Clear data, reload UI.

### 🥉 Hypothesis 3: Legacy Script Usage (Confidence: 5%)
**Root Cause:** `check-dashboard-*.js` scripts might be running and failing auth.
**Evidence:**
- **Weakness:** `check-dashboard-now.js` uses a hardcoded password (`namastex888`), not the API key placeholder string found in the logs.
**Location:** `check-dashboard-now.js`
**Fix Approach:** N/A (Unlikely to be the cause)
**Regression Check:** N/A

## Recommendation
Implement **Hypothesis 1 Fix**. The Gateway is the confirmed source of the noise.

**Proposed Fix:**
Edit `gateway/src/health.ts`:
1.  Add a check in `constructor` or `getOmniInstanceKeys` to identify the placeholder.
2.  If detected, skip the API call.
