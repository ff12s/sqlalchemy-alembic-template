import pytest

import db_models.cli.run_migration as rm
import db_models.cli.upgrade_migration as um


@pytest.fixture
def record_dispatch(monkeypatch):
    """Подменяет upgrade/downgrade на запись вызовов вместо реального запуска alembic."""
    calls = {"upgrade": [], "downgrade": []}
    monkeypatch.setattr(rm, "upgrade", lambda env: calls["upgrade"].append(env))
    monkeypatch.setattr(rm, "downgrade", lambda env, rev: calls["downgrade"].append((env, rev)))
    return calls


def test_no_downgrade_revision_dispatches_to_upgrade(record_dispatch, monkeypatch):
    monkeypatch.delenv("DOWNGRADE_REVISION", raising=False)
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    rm.main()
    assert record_dispatch["upgrade"] == ["dev"]
    assert record_dispatch["downgrade"] == []


def test_downgrade_revision_dispatches_to_downgrade(record_dispatch, monkeypatch):
    monkeypatch.setenv("DOWNGRADE_REVISION", "-1")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    rm.main()
    assert record_dispatch["downgrade"] == [("dev", "-1")]
    assert record_dispatch["upgrade"] == []


def test_blank_downgrade_revision_treated_as_unset(record_dispatch, monkeypatch):
    monkeypatch.setenv("DOWNGRADE_REVISION", "   ")
    monkeypatch.setenv("MIGRATION_ENV", "main")
    rm.main()
    assert record_dispatch["upgrade"] == ["main"]
    assert record_dispatch["downgrade"] == []


def test_unset_env_fails_fast_without_invoking_alembic(monkeypatch):
    """run-migration с пустым MIGRATION_ENV завершается ошибкой, не вызывая alembic (реальный upgrade)."""
    called = []
    monkeypatch.setattr(um, "run_alembic", lambda args, env: called.append((args, env)))
    monkeypatch.delenv("DOWNGRADE_REVISION", raising=False)
    monkeypatch.delenv("MIGRATION_ENV", raising=False)
    with pytest.raises(SystemExit):
        rm.main()
    assert called == []
