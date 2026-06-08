"""Применение миграций до head для одного тира или для всех (``all``)."""

from __future__ import annotations

import os
import sys

from db_models.cli.utils import run_alembic
from db_models.models import LADDER, Tier


def upgrade(environment: str) -> None:
    """Применить миграции до head для указанного тира или для всех тиров.

    Для ``all`` тиры обходятся снизу вверх по лесенке (dev → main),
    каждый в отдельном процессе alembic.

    :param environment: Имя тира (``main``/``dev``) либо ``all``.
    :raises SystemExit: При пустом или неизвестном значении тира.
    """
    environment = environment.strip().lower()
    if not environment:
        print(
            """Usage: upgrade-migration <main|dev|all>
            MIGRATION_ENV=<env> upgrade-migration""",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if environment == "all":
        for tier in reversed(LADDER):
            target = f"{tier.value}@head"
            print(f"Applying migrations for {tier.value} ({target})")
            run_alembic(["upgrade", target], tier.value)
        return

    try:
        tier = Tier(environment)
    except ValueError:
        allowed = ", ".join(t.value for t in LADDER) + ", all"
        print(f"Unsupported environment: {environment}. Allowed: {allowed}", file=sys.stderr)
        raise SystemExit(1) from None

    target = f"{tier.value}@head"
    print(f"Applying migrations for {tier.value} ({target})")
    run_alembic(["upgrade", target], tier.value)


def main() -> None:
    """Точка входа консольной команды ``upgrade-migration``.

    Тир берётся из первого аргумента, иначе из переменной ``MIGRATION_ENV``.
    """
    environment = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MIGRATION_ENV", "")
    upgrade(environment)


if __name__ == "__main__":
    main()
