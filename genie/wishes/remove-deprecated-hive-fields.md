# 🧞 Wish: Remove deprecated hive_ fields and legacy code

## 📋 Context & Objective

### 🎯 Primary Goal
Complete removal of all deprecated `hive_` fields from database, models, and codebase; remove legacy Hive fallbacks in services; ensure unified `agent_*` fields are the only source of truth.

### 📊 Current Status
- **Progress**: 40% (migration exists; unified models in place)
- **Last Updated**: 2025-09-18 00:00
- **Assigned Agents**: automagik-omni-genie-dev-coder

### 🔍 Background Context
Legacy `hive_` columns were temporarily kept for backward compatibility alongside unified `agent_*` fields. We are now removing them fully.

## 🧠 Shared Knowledge Base

### ✅ Discoveries
- Alembic migration `3d824d2d6df9_remove_legacy_hive_fields.py` drops all `hive_*` columns.
- `src/db/models.py` already uses unified `agent_*` fields; no `hive_` fields defined.
- `src/services/message_router.py` uses unified config and references `AutomagikHiveClient` for Hive instances but no `hive_` fallbacks.
- `src/services/automagik_hive_client.py` relies entirely on unified fields or dict overrides; no `hive_` fallbacks.
- No `src/api/schemas/automagik_hive.py` file; `src/api/schemas/omni.py` is present.
- No `src/utils/automagik_hive_validation.py` file.
- Tests reference Hive behavior via unified fields but not `hive_` columns; acceptable.

### 🚨 Issues Found
- None blocking. Need to ensure imports of `automagik_hive_models` are still required.

### 💡 Solutions Applied
- Confirmed migration and code paths free of `hive_` usage.

### ❌ Approaches That Failed
- N/A

## 📂 Relevant Files
- `alembic/versions/3d824d2d6df9_remove_legacy_hive_fields.py`
- `src/db/models.py`
- `src/services/message_router.py`
- `src/services/automagik_hive_client.py`
- `src/services/automagik_hive_models.py`
- `tests/test_omni_models.py`

## 🎯 Success Criteria
- Migration drops all `hive_*` columns
- No `hive_` fields in models
- No `has_hive_config()` or `get_hive_config()` legacy methods
- No `hive_` fallbacks in MessageRouter or AutomagikHiveClient
- No hive-only schemas/validations remain
- Repo-wide search finds no `hive_` references except migrations

## 📝 Agent Updates Log

### 2025-09-18 00:00 - automagik-omni-genie-dev-coder
- Verified migration exists and removes `hive_*` columns. Confirmed unified models and services; no remaining fallbacks.
