## Council Advisory

### Topic: Credential Management & Zero Config Transition
### Members Consulted: Sentinel, Deployer, Operator

### Perspectives

**Sentinel (Security):**
- **Analysis:** The server logs show `your-secret-api-key-here` being sent over the wire. This is a placeholder from `.env.example`. The server correctly rejects it, but the fact it's being sent means a client is misconfigured.
- **Vote:** MODIFY
- **Rationale:** We must ensure the placeholder key is NEVER accepted. The current behavior (rejecting it) is correct, but the client's persistence of this insecure default is the vulnerability.
- **Recommendation:** Modify `src/api/deps.py` to specifically detect this placeholder and return a specific error code (e.g., 412 Precondition Failed) or a clear message telling the client to reset.

**Deployer (Zero-Config):**
- **Analysis:** The goal is "Zero Config" (no `.env`). However, `src/config.py` still loads `.env`. This creates a "split brain" where the file system says one thing (placeholder) and the DB says another (generated key).
- **Vote:** APPROVE (with changes)
- **Rationale:** The bootstrapping logic in `src/db/bootstrap_settings.py` is sound (migrates or generates). The problem is the legacy config loading.
- **Recommendation:** Deprecate `.env` loading for the API key. The `ApiConfig` should default to `None` or look ONLY at the DB after the initial bootstrap. If `.env` exists, we should warn but prioritize the DB.

**Operator (Ops):**
- **Analysis:** The logs are flooded with "API key mismatch". This obscures real issues. The source is `127.0.0.1`, likely a local script or a developer's open tab.
- **Vote:** MODIFY
- **Rationale:** We need to silence the known-bad placeholder warning or make it actionable.
- **Recommendation:** In `src/api/deps.py`, if the received key is the known placeholder, log a DEBUG message instead of WARNING, or log it *once* per startup. And help the user find the zombie client.

### Synthesized Recommendation
The "Zero Config" transition is incomplete. The backend correctly prefers the DB key, but the environment loading mechanism (`src/config.py`) and the client's persisted state (localStorage) are causing conflicts.

**Action Plan:**
1.  **Update `src/api/deps.py`:** Explicitly catch the `your-secret-api-key-here` placeholder. If received, log a helpful message ("Client using placeholder key - requires re-auth") and return 401.
2.  **Update `src/config.py`:** Stop defaulting `api_key` to the env var *if* it matches the placeholder.
3.  **Client Cleanup:** The user needs to clear their browser's `localStorage` or update their scripts.

### User Decision Required
The council advises modifying the backend to handle the placeholder key more gracefully and enforcing the DB-first configuration. Proceed?
