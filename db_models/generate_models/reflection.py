import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def discover_schema_package(schema: str) -> tuple[Path, str]:
    schema_dir = REPO_ROOT / "models" / schema
    init_file = schema_dir / "__init__.py"
    if not init_file.exists():
        print(
            f"Error: models/{schema}/__init__.py not found. Run create-schema {schema} first.",
            file=sys.stderr,
        )
        sys.exit(1)

    content = init_file.read_text(encoding="utf-8")
    match = re.search(r"^class (Base\w+)\(Base\):", content, re.MULTILINE)
    if not match:
        print(
            f"Error: Cannot find base class in models/{schema}/__init__.py",
            file=sys.stderr,
        )
        sys.exit(1)

    return schema_dir, match.group(1)


@dataclass
class TableInfo:
    table_name: str
    columns: list[dict]
    pk_constraint: dict
    foreign_keys: list[dict]
    check_constraints: list[dict]
    unique_constraints: list[dict]
    indexes: list[dict]


def reflect_table(inspector: Any, table: str, schema: str) -> TableInfo:
    return TableInfo(
        table_name=table,
        columns=inspector.get_columns(table, schema=schema),
        pk_constraint=inspector.get_pk_constraint(table, schema=schema),
        foreign_keys=inspector.get_foreign_keys(table, schema=schema),
        check_constraints=inspector.get_check_constraints(table, schema=schema),
        unique_constraints=inspector.get_unique_constraints(table, schema=schema),
        indexes=inspector.get_indexes(table, schema=schema),
    )
