"""Корень репозитория (каталог с ``alembic.ini``) для запуска alembic командой создания миграций."""

from db_models.cli.utils import alembic_root

ROOT = alembic_root()
