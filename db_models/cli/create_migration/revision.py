"""Создание одной alembic-ревизии для контура (через отдельный процесс ``alembic``)."""

from __future__ import annotations

import configparser
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util import CommandError

from db_models.cli.create_migration.emptiness import find_created_revision, snapshot_py_files
from db_models.cli.create_migration.paths import ROOT

if TYPE_CHECKING:
    from pathlib import Path


def make_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


def branch_has_head(env: str) -> bool:
    script = ScriptDirectory.from_config(make_config())
    try:
        revs = script.get_revisions(f"{env}@head")
    except CommandError:
        return False
    return bool(revs)


def revision_extra_args(env: str) -> list[str]:
    if branch_has_head(env):
        return ["--head", f"{env}@head"]
    return ["--branch-label", env, "--head", "base"]


def write_env_ini(version_path: Path, dest: Path) -> None:
    """Записать временный alembic.ini с version_locations, ограниченным одним env."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(str(ROOT / "alembic.ini"))
    parser["alembic"]["version_locations"] = str(version_path)
    with dest.open("w", encoding="utf-8") as f:
        parser.write(f)


def current_heads(env: str, tmp_ini: Path) -> list[str]:
    env_vars = os.environ.copy()
    env_vars["MIGRATION_ENV"] = env
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(tmp_ini), "current"],
        cwd=ROOT,
        env=env_vars,
        capture_output=True,
        text=True,
    )
    heads = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("INFO"):
            heads.append(line)
    return heads


def run_revision(env: str, message: str, *, autogenerate: bool) -> Path | None:
    """Создать ревизию для контура ``env`` и вернуть путь созданного файла.

    :param env: Имя контура (тира).
    :param message: Сообщение ревизии.
    :param autogenerate: Запускать ли autogenerate (иначе пустой шаблон).
    :return: Путь созданной ревизии либо ``None``.
    :raises SystemExit: Если БД не на head или alembic завершился с ошибкой.
    """
    version_path = ROOT / "migrations" / "versions" / env
    version_path.mkdir(parents=True, exist_ok=True)

    before = snapshot_py_files(version_path)

    tmp_ini = ROOT / f".alembic_{env}.ini"
    write_env_ini(version_path, tmp_ini)

    cmd = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(tmp_ini),
        "revision",
        "-m",
        message,
        "--version-path",
        str(version_path.relative_to(ROOT)),
    ]
    if autogenerate:
        cmd.append("--autogenerate")
    cmd.extend(revision_extra_args(env))

    env_vars = os.environ.copy()
    env_vars["MIGRATION_ENV"] = env

    try:
        result = subprocess.run(cmd, cwd=ROOT, check=False, env=env_vars, capture_output=True, text=True)
        if result.returncode != 0:
            if "Target database is not up to date" in result.stderr:
                heads = current_heads(env, tmp_ini)
                heads_str = ", ".join(heads) if heads else "(none — not stamped)"
                raise SystemExit(
                    f"ERROR [{env}] database is not up to date.\n"
                    f"  Current DB head : {heads_str}\n"
                    f"  Run first: upgrade-migration {env}"
                )
            sys.stderr.write(result.stderr)
            raise SystemExit(f"ERROR [{env}] alembic revision failed (exit {result.returncode})")
        sys.stderr.write(result.stderr)
    finally:
        tmp_ini.unlink(missing_ok=True)

    after = snapshot_py_files(version_path)
    return find_created_revision(before, after)
