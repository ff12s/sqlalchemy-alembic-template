from pathlib import Path

from db_models.models import _collect_override_stems


def touch(directory: Path, name: str) -> None:
    (directory / f"{name}.py").write_text("# placeholder\n")


# ── override на dev виден только из dev ───────────────────────────────────────


def test_dev_override_visible_from_dev(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "tbl")
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _collect_override_stems(tmp_path) == {"tbl"}


def test_dev_override_not_visible_from_main(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    touch(tmp_path / "dev", "tbl")
    monkeypatch.setenv("MIGRATION_ENV", "main")
    assert _collect_override_stems(tmp_path) == set()


# ── несколько таблиц переопределены в dev ─────────────────────────────────────


def test_dev_sees_all_dev_overrides(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    for name in ("tbl_a", "tbl_b"):
        touch(tmp_path / "dev", name)
    monkeypatch.setenv("MIGRATION_ENV", "dev")
    assert _collect_override_stems(tmp_path) == {"tbl_a", "tbl_b"}


def test_main_sees_no_overrides(tmp_path, monkeypatch):
    (tmp_path / "dev").mkdir()
    for name in ("tbl_a", "tbl_b"):
        touch(tmp_path / "dev", name)
    monkeypatch.setenv("MIGRATION_ENV", "main")
    assert _collect_override_stems(tmp_path) == set()
