from pathlib import Path

import pytest

from db_models.models import _shadowed_stems


def touch(directory: Path, name: str) -> None:
    (directory / f"{name}.py").write_text("# placeholder\n")


# ── не tier-подпакет → затенения нет ─────────────────────────────────────────


def test_non_tier_package_returns_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "tbl")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    # tmp_path сам по себе не является tier-папкой.
    assert _shadowed_stems(tmp_path) == set()


def test_unknown_tier_dir_returns_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Имя, которого нет в LADDER, не распознаётся как tier-подпакет.
    (tmp_path / "staging").mkdir()
    touch(tmp_path / "staging", "tbl")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _shadowed_stems(tmp_path / "staging") == set()


# ── dev — самый специфичный тир, его файлы не затеняются ──────────────────────


def test_dev_subpackage_is_never_shadowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "tbl")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _shadowed_stems(tmp_path / "dev") == set()


# ── механизм затенения: более специфичный активный тир (dev) затеняет stem ─────
#    (на 2-тировой лестнице это единственный возможный случай затенения).


def test_more_specific_active_tier_shadows_stem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main").mkdir()
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "main", "tbl")
    touch(tmp_path / "dev", "tbl")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _shadowed_stems(tmp_path / "main") == {"tbl"}


def test_not_shadowed_when_more_specific_tier_inactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main").mkdir()
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "main", "tbl")
    touch(tmp_path / "dev", "tbl")
    monkeypatch.setenv("MIGRATION_ENV", "main")
    assert _shadowed_stems(tmp_path / "main") == set()
