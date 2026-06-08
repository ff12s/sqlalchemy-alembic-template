import sys

import pytest

import db_models.cli.downgrade_migration as dm


@pytest.fixture
def record_alembic(monkeypatch):
    """Подменяет run_alembic на запись (args, env) без запуска alembic."""
    calls = []
    monkeypatch.setattr(dm, "run_alembic", lambda args, env: calls.append((args, env)))
    return calls


def test_downgrade_runs_alembic(record_alembic):
    dm.downgrade("dev", "-1")
    assert record_alembic == [(["downgrade", "-1"], "dev")]


def test_missing_env_exits(record_alembic):
    with pytest.raises(SystemExit):
        dm.downgrade("", "-1")
    assert record_alembic == []


def test_missing_revision_exits(record_alembic):
    with pytest.raises(SystemExit):
        dm.downgrade("dev", "")
    assert record_alembic == []


def test_downgrade_forwards_revision_verbatim(record_alembic):
    dm.downgrade("main", "ae1027a6acf")
    assert record_alembic == [(["downgrade", "ae1027a6acf"], "main")]


def test_main_reads_env_for_tier_and_argv_for_revision(monkeypatch):
    seen = []
    monkeypatch.setattr(dm, "downgrade", lambda env, rev: seen.append((env, rev)))
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    monkeypatch.setattr(sys, "argv", ["downgrade-migration", "-1"])
    dm.main()
    assert seen == [("dev", "-1")]


def test_main_without_revision_exits_without_invoking_alembic(monkeypatch):
    """downgrade-migration без аргумента-ревизии завершается ошибкой, не вызывая alembic (реальный downgrade)."""
    called = []
    monkeypatch.setattr(dm, "run_alembic", lambda args, env: called.append((args, env)))
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    monkeypatch.setattr(sys, "argv", ["downgrade-migration"])
    with pytest.raises(SystemExit):
        dm.main()
    assert called == []
