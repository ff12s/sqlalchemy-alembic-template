import sys

import pytest

import db_models.cli.upgrade_migration as um


@pytest.fixture
def record_alembic(monkeypatch):
    """Подменяет run_alembic на запись (args, env) без запуска alembic."""
    calls = []
    monkeypatch.setattr(um, "run_alembic", lambda args, env: calls.append((args, env)))
    return calls


def test_single_tier_upgrades_to_head(record_alembic):
    um.upgrade("dev")
    assert record_alembic == [(["upgrade", "dev@head"], "dev")]


def test_all_iterates_ladder_bottom_up(record_alembic):
    um.upgrade("all")
    assert record_alembic == [
        (["upgrade", "dev@head"], "dev"),
        (["upgrade", "main@head"], "main"),
    ]


def test_tier_is_case_insensitive(record_alembic):
    um.upgrade("DEV")
    assert record_alembic == [(["upgrade", "dev@head"], "dev")]


def test_unknown_tier_exits(record_alembic):
    with pytest.raises(SystemExit):
        um.upgrade("nope")
    assert record_alembic == []


def test_empty_tier_exits(record_alembic):
    with pytest.raises(SystemExit):
        um.upgrade("")
    assert record_alembic == []


@pytest.fixture
def record_upgrade(monkeypatch):
    """Подменяет upgrade на запись переданного тира (для тестов main())."""
    seen = []
    monkeypatch.setattr(um, "upgrade", lambda env: seen.append(env))
    return seen


def test_main_arg_takes_precedence_over_env(record_upgrade, monkeypatch):
    monkeypatch.setenv("MIGRATION_ENV", "main")
    monkeypatch.setattr(sys, "argv", ["upgrade-migration", "dev"])
    um.main()
    assert record_upgrade == ["dev"]


def test_main_falls_back_to_env_when_no_arg(record_upgrade, monkeypatch):
    monkeypatch.setenv("MIGRATION_ENV", "main")
    monkeypatch.setattr(sys, "argv", ["upgrade-migration"])
    um.main()
    assert record_upgrade == ["main"]
