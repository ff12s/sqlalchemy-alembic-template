"""Запуск миграции по окружению: откат при ``DOWNGRADE_REVISION``, иначе апгрейд до head."""

from __future__ import annotations

import os

from db_models.cli.downgrade_migration import downgrade
from db_models.cli.upgrade_migration import upgrade


def main() -> None:
    """Точка входа консольной команды ``run-migration`` (CMD контейнера миграций).

    Если задан ``DOWNGRADE_REVISION`` — откат до неё, иначе апгрейд до head.
    Тир во всех случаях берётся из ``MIGRATION_ENV``.
    """
    revision = os.environ.get("DOWNGRADE_REVISION", "").strip()
    environment = os.environ.get("MIGRATION_ENV", "")
    if revision:
        downgrade(environment, revision)
    else:
        upgrade(environment)


if __name__ == "__main__":
    main()
