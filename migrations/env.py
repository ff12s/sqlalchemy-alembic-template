import configparser
from logging.config import fileConfig
from typing import Any

import sqlalchemy as sa
from alembic import context
from sqlalchemy import engine_from_config, pool

from db_models.config import SQLALCHEMY_DATABASE_URI, get_migration_env
from db_models.models import ENV_ALLOWED_TIERS, Base, Tier, tier_of_module
from migrations.migration_filters import (
    compare_server_default as _compare_server_default,
    fk_signature as _fk_signature,
    normalize_schema_name as _normalize_schema_name,
    table_key as _table_key,
)

config = context.config
section = config.config_ini_section
# URL не перезаписываем, если его уже задал вызывающий (например, scripts/db.py).
try:
    _url_already_set = bool(config.get_main_option("sqlalchemy.url", None))
except configparser.InterpolationMissingOptionError:
    _url_already_set = False
if not _url_already_set:
    config.set_section_option(section, "SQLALCHEMY_DATABASE_URL", SQLALCHEMY_DATABASE_URI)
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Каждый контур включает свои таблицы и все нижестоящие по лестнице.
MIGRATION_ENV = get_migration_env()


def _collect_allowed_table_keys(env: Tier) -> set[str]:
    allowed: set[str] = set()
    allowed_tiers = ENV_ALLOWED_TIERS[env]

    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        if tier_of_module(model_class.__module__) not in allowed_tiers:
            continue
        table = mapper.local_table
        allowed.add(_table_key(table.schema, table.name))  # ty:ignore[unresolved-attribute]

    # Table() на Base.metadata без ORM-mapper: явный контур через info["migration_tier"].
    for table in Base.metadata.tables.values():
        tier = table.info.get("migration_tier")
        if tier is None or tier not in allowed_tiers:
            continue
        allowed.add(_table_key(table.schema, table.name))

    return allowed


ALLOWED_TABLE_KEYS = _collect_allowed_table_keys(MIGRATION_ENV)
ALLOWED_SCHEMAS = {key.rsplit(".", 1)[0] for key in ALLOWED_TABLE_KEYS if "." in key}
# Схемы сервиса: autogenerate видит все reflected-таблицы, чтобы удаление модели стало drop_table.
OWNED_SCHEMAS: set[str] = {_normalize_schema_name(table.schema) for table in Base.metadata.tables.values()}


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    if type_ == "schema":
        # default schema PostgreSQL: name может быть None — не отсекаем, иначе public-таблицы выпадут из сравнения.
        if name is None:
            return True
        return name in ALLOWED_SCHEMAS or name in OWNED_SCHEMAS

    if type_ == "table":
        if name is None:
            return False
        schema_name = parent_names.get("schema_name")
        # В наших схемах пропускаем все reflected-таблицы, иначе удаление модели не станет drop_table.
        if _normalize_schema_name(schema_name) in OWNED_SCHEMAS:
            return True
        key = _table_key(schema_name, name)
        if key in ALLOWED_TABLE_KEYS:
            return True

        # Fallback для default schema, где public может прийти как schema=None.
        return bool(schema_name is None and _table_key("public", name) in ALLOWED_TABLE_KEYS)

    return True


def include_object(
    object_: Any,  # noqa: ANN401
    name: str | None,  # noqa: ARG001
    type_: str,
    reflected: bool,
    compare_to: Any,  # noqa: ANN401
) -> bool:
    if type_ == "column" and not reflected and getattr(object_, "info", {}).get("skip_autogenerate"):
        return False

    # Подавляем шумовой diff, когда FK тот же, а различие лишь в представлении default schema (None vs public).
    if type_ == "foreign_key_constraint" and compare_to is not None:
        object_signature = _fk_signature(object_)
        compare_signature = _fk_signature(compare_to)
        if object_signature is not None and object_signature == compare_signature:
            return False

    return True


def _process_revision_directives(
    context: Any,  # noqa: ANN401, ARG001
    revision: Any,  # noqa: ANN401, ARG001
    directives: list[Any],
) -> None:
    for directive in directives:
        upgrade_ops = getattr(directive, "upgrade_ops", None)
        if upgrade_ops is None:
            continue
        for op in upgrade_ops.ops:
            if type(op).__name__ == "CreateSequenceOp":
                op.if_not_exists = True


def _create_schemas_sql() -> list[str]:
    return [f"CREATE SCHEMA IF NOT EXISTS {schema}" for schema in sorted(ALLOWED_SCHEMAS) if schema != "public"]


def run_migrations_offline() -> None:
    """Запускает миграции в offline-режиме: контекст настраивается по URL без Engine."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,  # ty:ignore[invalid-argument-type]
        include_object=include_object,
        compare_type=True,
        include_sequences=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_server_default=_compare_server_default,  # ty:ignore[invalid-argument-type]
        process_revision_directives=_process_revision_directives,
    )

    with context.begin_transaction():
        for stmt in _create_schemas_sql():
            context.execute(stmt)
        context.run_migrations()


def run_migrations_online() -> None:
    """Запускает миграции в online-режиме: создаёт Engine и связывает соединение с контекстом."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),  # ty:ignore[invalid-argument-type]
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,  # ty:ignore[invalid-argument-type]
            include_object=include_object,
            compare_type=True,
            include_sequences=True,
            compare_server_default=_compare_server_default,  # ty:ignore[invalid-argument-type]
            process_revision_directives=_process_revision_directives,
        )

        with context.begin_transaction():
            for stmt in _create_schemas_sql():
                connection.execute(sa.text(stmt))
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
