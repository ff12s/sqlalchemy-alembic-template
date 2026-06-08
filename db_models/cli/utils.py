"""Общие хелперы консольных команд: поиск корня репозитория и запуск alembic."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    """Найти корень исходного дерева репозитория — каталог с ``alembic.ini``.

    Поиск идёт вверх от расположения этого файла, поэтому работает из любого
    рабочего каталога при editable-установке пакета.

    :return: Каталог, содержащий ``alembic.ini``.
    :raises RuntimeError: Если ``alembic.ini`` не найден ни в одном родителе
        (пакет установлен не из source-checkout).
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "alembic.ini").is_file():
            return parent
    raise RuntimeError(
        "alembic.ini не найден над db_models/cli — команда требует source-checkout "
        "(установите пакет editable: pip install -e .)"
    )


def alembic_root() -> Path:
    """Определить каталог, относительно которого запускать alembic.

    Если ``alembic.ini`` есть в текущем рабочем каталоге — берётся он (контейнер
    с ``WORKDIR`` либо запуск из корня репозитория), иначе ``repo_root()``.

    :return: Каталог с ``alembic.ini``.
    """
    cwd = Path.cwd()
    if (cwd / "alembic.ini").is_file():
        return cwd
    return repo_root()


def run_alembic(args: list[str], env: str) -> None:
    """Запустить alembic отдельным процессом под нужным тиром.

    Процесс стартует с ``cwd`` = каталог с ``alembic.ini`` (в нём ``script_location``
    и ``prepend_sys_path`` заданы относительно CWD) и с ``MIGRATION_ENV``, выставленным
    до импорта моделей в ``env.py``.

    :param args: Аргументы alembic после ``-c <ini>`` (например ``["upgrade", "dev@head"]``).
    :param env: Значение ``MIGRATION_ENV`` для дочернего процесса.
    :raises subprocess.CalledProcessError: Если alembic завершился с ненулевым кодом.
    """
    root = alembic_root()
    env_vars = os.environ.copy()
    env_vars["MIGRATION_ENV"] = env
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(root / "alembic.ini"), *args],
        cwd=root,
        env=env_vars,
        check=True,
    )
