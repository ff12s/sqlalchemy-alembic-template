from typing import Any

from alembic import op
from sqlalchemy import inspect
from sqlalchemy.engine.reflection import Inspector


def get_inspector() -> Inspector:
    bind = op.get_context().bind
    if bind is None:
        raise RuntimeError("Alembic context не привязан к соединению")
    return inspect(bind)


def column_exists(table_name: str, column_name: str, schema: str | None = None) -> bool:
    inspector = get_inspector()
    columns = inspector.get_columns(table_name, schema=schema)
    return any(c["name"] == column_name for c in columns)


def table_exists(table_name: str, schema: str | None = None) -> bool:
    inspector = get_inspector()
    return table_name in inspector.get_table_names(schema=schema)


def schema_exists(schema: str) -> bool:
    inspector = get_inspector()
    return inspector.has_schema(schema)


def index_exists(index_name: str, table_name: str, schema: str | None = None) -> bool:
    inspector = get_inspector()
    indexes = inspector.get_indexes(table_name, schema=schema)
    return any(i["name"] == index_name for i in indexes)


def get_column_type(table_name: str, column_name: str, schema: str | None = None) -> Any | None:  # noqa: ANN401
    inspector = get_inspector()
    columns = inspector.get_columns(table_name, schema=schema)

    for c in columns:
        if c["name"] == column_name:
            return c["type"]

    return None
