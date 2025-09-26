"""Tests for FastAPI startup sequencing and migration gating."""

import sys
import types

import pytest
from fastapi import FastAPI

import src.api.app as app_module


class _DummySession:
    """Simple context manager stub used to replace SessionLocal."""

    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture(autouse=True)
def _stub_dependent_services(monkeypatch):
    """Provide lightweight stand-ins for services imported inside lifespan."""
    monkeypatch.setenv("ENVIRONMENT", "dev")

    access_control_stub = types.SimpleNamespace(load_rules=lambda db: None)
    discovery_stub = types.SimpleNamespace(discover_evolution_instances=lambda db: [])

    monkeypatch.setitem(
        sys.modules,
        "src.services.access_control",
        types.SimpleNamespace(access_control_service=access_control_stub),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.services.discovery_service",
        types.SimpleNamespace(discovery_service=discovery_stub),
    )

    from src.db import database as database_module

    monkeypatch.setattr(database_module, "SessionLocal", lambda: _DummySession())

    yield

    monkeypatch.delenv("ENVIRONMENT", raising=False)


@pytest.mark.asyncio
async def test_lifespan_runs_migrations_before_creating_tables(monkeypatch):
    """Migrations should execute before table creation to avoid side-effects on stale schemas."""
    call_order: list[str] = []

    from src.db import database as database_module
    from src.db import migrations as migrations_module

    def record_tables():
        call_order.append("create_tables")

    def record_migrations():
        call_order.append("auto_migrate")
        return True

    monkeypatch.setattr(app_module, "create_tables", record_tables)
    monkeypatch.setattr(database_module, "create_tables", record_tables)
    monkeypatch.setattr(migrations_module, "auto_migrate", record_migrations)

    async with app_module.lifespan(FastAPI()):
        pass

    assert call_order, "Expected startup hooks to run"
    assert call_order.index("auto_migrate") < call_order.index("create_tables"), call_order


@pytest.mark.asyncio
async def test_lifespan_aborts_when_migrations_fail(monkeypatch):
    """Application startup must halt when migrations cannot be applied."""
    call_order: list[str] = []

    from src.db import database as database_module
    from src.db import migrations as migrations_module

    def record_tables():
        call_order.append("create_tables")

    def failing_migrations():
        call_order.append("auto_migrate")
        return False

    monkeypatch.setattr(app_module, "create_tables", record_tables)
    monkeypatch.setattr(database_module, "create_tables", record_tables)
    monkeypatch.setattr(migrations_module, "auto_migrate", failing_migrations)

    with pytest.raises(RuntimeError):
        async with app_module.lifespan(FastAPI()):
            pass

    assert call_order == ["auto_migrate"], "create_tables should not run after migration failure"
