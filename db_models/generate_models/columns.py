import re
from dataclasses import dataclass
from typing import Any

from db_models.generate_models.reflection import TableInfo

CATEGORY_ORDER = {
    "pk": 0,
    "required_fk": 1,
    "required": 2,
    "nullable_fk": 3,
    "nullable": 4,
    "server_default": 5,
}


def map_sa_type(sa_type: Any) -> tuple[str, str]:  # noqa: ANN401
    """Returns (rendered_type_str, python_hint)."""
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Date,
        DateTime,
        Float,
        Integer,
        Numeric,
        SmallInteger,
        String,
        Text,
        Time,
    )
    from sqlalchemy.dialects.postgresql import JSONB

    if isinstance(sa_type, JSONB):
        return "JSONB", "dict[str, Any]"
    if isinstance(sa_type, BigInteger):
        return "BigInteger", "int"
    if isinstance(sa_type, SmallInteger):
        return "SmallInteger", "int"
    if isinstance(sa_type, Integer):
        return "Integer", "int"
    if isinstance(sa_type, Text):
        return "Text", "str"
    if isinstance(sa_type, String):
        return (f"String({sa_type.length})" if sa_type.length else "String"), "str"
    if isinstance(sa_type, Boolean):
        return "Boolean", "bool"
    if isinstance(sa_type, DateTime):
        return f"DateTime({getattr(sa_type, 'timezone', False)})", "datetime"
    if isinstance(sa_type, Date):
        return "Date", "date"
    if isinstance(sa_type, Time):
        return "Time", "time"
    if isinstance(sa_type, Float):
        return "REAL", "float"
    if isinstance(sa_type, Numeric):
        p, s = sa_type.precision, sa_type.scale
        return (f"Numeric({p}, {s})" if p is not None and s is not None else "Numeric"), "Decimal"
    return "Text  # TODO: check type", "str"


@dataclass
class PKInfo:
    kind: str  # "identity" | "sequence" | "plain"
    seq_name: str | None = None
    seq_schema: str | None = None
    identity_always: bool | None = None
    identity_start: int | None = None
    identity_increment: int | None = None
    identity_minvalue: int | None = None
    identity_maxvalue: int | None = None


def classify_pk_column(col_dict: dict, schema: str) -> PKInfo:
    identity = col_dict.get("identity")
    if identity:
        return PKInfo(
            kind="identity",
            identity_always=identity.get("always"),
            identity_start=identity.get("start"),
            identity_increment=identity.get("increment"),
            identity_minvalue=identity.get("minvalue"),
            identity_maxvalue=identity.get("maxvalue"),
        )

    default = col_dict.get("default") or ""
    if default.startswith("nextval("):
        m = re.search(r"nextval\('([^']+)'", default)
        if m:
            seq_full = m.group(1)
            if "." in seq_full:
                seq_schema, seq_name = seq_full.split(".", 1)
            else:
                seq_schema, seq_name = schema, seq_full
            return PKInfo(kind="sequence", seq_name=seq_name, seq_schema=seq_schema)

    return PKInfo(kind="plain")


def parse_server_default(raw: str | None) -> tuple[str | None, str | None]:
    """Returns (server_default_expr, python_default_expr) for use in code."""
    if raw is None:
        return None, None
    if raw.startswith("nextval("):
        return None, None

    r = raw.strip()

    if r == "now()":
        return 'text("now()")', 'text("now()")'
    if r == "CURRENT_TIMESTAMP":
        return 'text("CURRENT_TIMESTAMP")', 'text("CURRENT_TIMESTAMP")'

    for bool_raw, bool_val in [
        ("'false'", "False"),
        ("'true'", "True"),
        ("false", "False"),
        ("true", "True"),
        ("'false'::boolean", "False"),
        ("'true'::boolean", "True"),
    ]:
        if r == bool_raw:
            escaped = r.replace('"', '\\"')
            return f'text("{escaped}")', bool_val

    m = re.match(r"^(\d+)$", r) or re.match(r"^'(\d+)'::integer$", r)
    if m:
        return f'text("{r}")', m.group(1)

    m = re.match(r"^'([^']*)'::character varying$", r)
    if m:
        val = m.group(1)
        return f"text(\"'{val}'\")", f'"{val}"'

    m = re.match(r"^'([^']*)'$", r)
    if m:
        return f'text("{r}")', f'"{m.group(1)}"'

    escaped = r.replace('"', '\\"')
    return f'text("{escaped}")', f'text("{escaped}")  # TODO: verify default'


@dataclass
class ColumnData:
    name: str
    type_str: str
    python_hint: str
    nullable: bool
    is_pk: bool
    pk_info: PKInfo | None
    fk_dict: dict | None
    server_default_expr: str | None
    python_default_expr: str | None
    category: str  # pk | required_fk | required | nullable_fk | nullable | server_default


def classify_columns(tinfo: TableInfo, schema: str) -> list[ColumnData]:
    pk_cols_set = set(tinfo.pk_constraint.get("constrained_columns", []))
    col_to_fk: dict[str, dict] = {}
    for fk in tinfo.foreign_keys:
        for col_name in fk.get("constrained_columns", []):
            col_to_fk[col_name] = fk

    result = []
    for col in tinfo.columns:
        col_name = col["name"]
        nullable = col["nullable"]
        type_str, python_hint = map_sa_type(col["type"])
        is_pk = col_name in pk_cols_set
        fk_dict = col_to_fk.get(col_name)

        if is_pk:
            pk_info = classify_pk_column(col, schema)
            sd_expr = py_default = None
        else:
            pk_info = None
            sd_expr, py_default = parse_server_default(col.get("default"))

        if is_pk:
            category = "pk"
        elif nullable:
            category = "nullable_fk" if fk_dict else "nullable"
        elif sd_expr is not None:
            category = "server_default"
        else:
            category = "required_fk" if fk_dict else "required"

        result.append(
            ColumnData(
                name=col_name,
                type_str=type_str,
                python_hint=python_hint,
                nullable=nullable,
                is_pk=is_pk,
                pk_info=pk_info,
                fk_dict=fk_dict,
                server_default_expr=sd_expr,
                python_default_expr=py_default,
                category=category,
            )
        )
    return result


def order_columns(cols: list[ColumnData]) -> list[ColumnData]:
    return sorted(cols, key=lambda c: CATEGORY_ORDER[c.category])
