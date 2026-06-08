from pathlib import Path

from db_models.models import _collect_override_stems


def touch(directory: Path, name: str) -> None:
    (directory / f"{name}.py").write_text("# placeholder\n")


# ── main (базовый тир) ──────────────────────────────────────────────────────────


def test_main_env_returns_empty_even_with_dev_files(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "some_table")
    monkeypatch.setenv("MIGRATION_ENV", "main")
    assert _collect_override_stems(tmp_path) == set()


# ── dev ─────────────────────────────────────────────────────────────────────────


def test_dev_env_finds_dev_override(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "some_table")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _collect_override_stems(tmp_path) == {"some_table"}


def test_dev_env_finds_multiple_overrides(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "foo")
    touch(tmp_path / "dev", "bar")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _collect_override_stems(tmp_path) == {"foo", "bar"}


def test_non_ladder_dirs_are_ignored(tmp_path, monkeypatch):
    # Папка с именем, которого нет в LADDER, тиром не считается и не сканируется.
    (tmp_path / "staging").mkdir()
    touch(tmp_path / "staging", "some_table")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _collect_override_stems(tmp_path) == set()
