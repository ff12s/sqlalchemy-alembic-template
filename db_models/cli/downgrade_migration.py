"""Откат миграций тира до указанной ревизии."""

from __future__ import annotations

import os
import sys

from db_models.cli.utils import run_alembic


def downgrade(environment: str, revision: str) -> None:
    """Откатить миграции тира ``environment`` до ревизии ``revision``.

    :param environment: Тир из ``MIGRATION_ENV`` (обязателен).
    :param revision: Целевая ревизия alembic (например ``-1`` или хэш ревизии).
    :raises SystemExit: Если не задан тир или ревизия.
    """
    environment = environment.strip()
    if not environment:
        print("MIGRATION_ENV is not set", file=sys.stderr)
        raise SystemExit(1)
    if not revision:
        print("Usage: MIGRATION_ENV=<env> downgrade-migration <revision>", file=sys.stderr)
        raise SystemExit(1)

    print(f"Downgrading {environment} to {revision}")
    run_alembic(["downgrade", revision], environment)


def main() -> None:
    """Точка входа консольной команды ``downgrade-migration``.

    Тир берётся из ``MIGRATION_ENV``, ревизия — из первого аргумента.
    """
    environment = os.environ.get("MIGRATION_ENV", "")
    revision = sys.argv[1] if len(sys.argv) > 1 else ""
    downgrade(environment, revision)


if __name__ == "__main__":
    main()
