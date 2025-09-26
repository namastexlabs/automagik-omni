"""Tests around Alembic migration utilities."""

from alembic.script import ScriptDirectory
from sqlalchemy.exc import OperationalError

from src.db import migrations as migrations_module
from src.db.migrations import get_alembic_config


def test_alembic_has_single_head():
    """Repositories should define a single Alembic head (merge when branches exist)."""
    script_dir = ScriptDirectory.from_config(get_alembic_config())
    heads = script_dir.get_heads()

    assert len(heads) == 1, f"Expected a single head, found: {heads}"
    assert heads[0] == "42a0f0c8f9f1"


def test_run_migrations_stamps_after_idempotent_error(monkeypatch):
    """If upgrade raises an idempotent schema error, run_migrations should stamp head."""

    def fake_upgrade(config, revision):
        raise OperationalError("upgrade", None, Exception("table foo already exists"))

    calls: list[str] = []

    def fake_stamp(revision: str = "head", timeout_seconds: int = 5) -> bool:
        calls.append(revision)
        return True

    monkeypatch.setattr(migrations_module.command, "upgrade", fake_upgrade)
    monkeypatch.setattr(migrations_module, "stamp_database", fake_stamp)
    monkeypatch.setattr(migrations_module, "get_current_revision", lambda: "old-rev")

    assert migrations_module.run_migrations() is True
    assert calls == ["head"]
