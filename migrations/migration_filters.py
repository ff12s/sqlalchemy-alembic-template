"""Чистые функции фильтрации для Alembic autogenerate.

Вынесены из ``migrations/env.py`` (который при импорте запускает миграции), чтобы
их можно было покрыть unit-тестами без подключения к БД.
"""

import re
from typing import Any

from sqlalchemy import ForeignKeyConstraint

FkSignature = tuple[str, str, str, str, tuple[str, ...], tuple[str, ...], str | None, str | None]

# Срезаем явные приведения типов ``::type``, которые PostgreSQL добавляет в server_default,
# а SQLAlchemy не рендерит: ``::numeric(11,2)``, ``::character varying(50)``, ``::integer[]`` и т.п.
# Аргумент приведения допускает один уровень вложенных скобок (``::t(f(x))``).
_CAST_SUFFIX = re.compile(r"::\s*[A-Za-z_]\w*(?:\s+[A-Za-z_]\w*)*(?:\s*\((?:[^()]|\([^()]*\))*\))?(?:\[\])*")


def normalize_schema_name(schema_name: str | None) -> str:
    """Приводит имя схемы к каноническому виду (``None`` → ``public``).

    :param schema_name: имя схемы или ``None`` для схемы по умолчанию
    :return: каноническое имя схемы
    """
    return schema_name or "public"


def table_key(schema: str | None, table_name: str) -> str:
    """Строит ключ ``schema.table`` (без схемы — просто имя таблицы).

    :param schema: имя схемы или ``None``
    :param table_name: имя таблицы
    :return: строковый ключ таблицы
    """
    return f"{schema}.{table_name}" if schema else table_name


def normalize_server_default(val: str | None) -> str | None:
    """Нормализует server_default, убирая PostgreSQL-приведения типов для сравнения.

    :param val: отрефлексированное или отрендеренное значение server_default
    :return: значение без хвостовых ``::type``-приведений либо ``None``
    """
    if val is None:
        return None
    return _CAST_SUFFIX.sub("", val).strip()


def compare_server_default(
    context: Any,  # noqa: ANN401, ARG001
    inspected_column: Any,  # noqa: ANN401, ARG001
    metadata_column: Any,  # noqa: ANN401, ARG001
    inspected_default: str | None,
    metadata_default: str | None,  # noqa: ARG001
    rendered_metadata_default: str | None,
) -> bool:
    """Сравнивает server_default БД и модели, игнорируя SERIAL/sequence и приведения типов.

    :param inspected_default: server_default, отрефлексированный из БД
    :param rendered_metadata_default: server_default модели, отрендеренный SQLAlchemy
    :return: ``True``, если значения различаются (требуется diff), иначе ``False``
    """
    # SERIAL/sequence: у модели нет server_default, а в БД есть nextval(...) — считаем равными.
    if rendered_metadata_default is None and (inspected_default or "").lstrip().startswith("nextval("):
        return False
    return normalize_server_default(inspected_default) != normalize_server_default(rendered_metadata_default)


def fk_signature(fk_constraint: ForeignKeyConstraint) -> FkSignature | None:
    """Возвращает сравнимую сигнатуру FK для подавления шумовых diff (``None`` vs ``public``).

    :param fk_constraint: ограничение внешнего ключа
    :return: кортеж-сигнатура либо ``None``, если таблицы ещё не привязаны
    """
    source_table = fk_constraint.table
    referred_table = fk_constraint.referred_table
    if source_table is None or referred_table is None:
        return None

    source_cols = tuple(element.parent.name for element in fk_constraint.elements)
    referred_cols = tuple(element.column.name for element in fk_constraint.elements)

    return (
        normalize_schema_name(source_table.schema),
        source_table.name,
        normalize_schema_name(referred_table.schema),
        referred_table.name,
        source_cols,
        referred_cols,
        fk_constraint.onupdate,
        fk_constraint.ondelete,
    )
