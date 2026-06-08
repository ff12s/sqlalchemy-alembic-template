from pathlib import Path

from db_models.models import _collect_override_stems


def touch(directory: Path, name: str) -> None:
    (directory / f"{name}.py").write_text("# placeholder\n")


# ── граничные случаи ──────────────────────────────────────────────────────────


def test_no_override_dirs_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _collect_override_stems(tmp_path) == set()


def test_init_py_not_treated_as_override_stem(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    (tmp_path / "dev" / "__init__.py").write_text("")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _collect_override_stems(tmp_path) == set()


def test_missing_migration_env_defaults_to_base(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "some_table")
    monkeypatch.delenv("MIGRATION_ENV", raising=False)
    # По умолчанию активен только базовый тир — override-ы dev не видны.
    assert _collect_override_stems(tmp_path) == set()


def test_invalid_migration_env_defaults_to_base(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "some_table")
    monkeypatch.setenv("MIGRATION_ENV", "staging")
    assert _collect_override_stems(tmp_path) == set()
