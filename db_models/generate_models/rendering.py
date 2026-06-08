from db_models.generate_models.columns import ColumnData, classify_columns, order_columns
from db_models.generate_models.reflection import TableInfo
from db_models.generate_models.relationships import RelInfo, pascal_case


def _fk_expr(fk_dict: dict, schema: str) -> str:
    ref_schema = fk_dict.get("referred_schema") or schema
    ref_table = fk_dict["referred_table"]
    ref_col = fk_dict["referred_columns"][0]
    options = fk_dict.get("options") or {}
    ondelete = options.get("ondelete")
    onupdate = options.get("onupdate")
    name = fk_dict.get("name")

    args = [f'"{ref_schema}.{ref_table}.{ref_col}"']
    if ondelete:
        args.append(f'ondelete="{ondelete}"')
    if onupdate:
        args.append(f'onupdate="{onupdate}"')
    if name:
        args.append(f'name="{name}"')
    return f"ForeignKey({', '.join(args)})"


def render_column(col: ColumnData, schema: str) -> str:
    hint = col.python_hint

    if col.is_pk:
        pk = col.pk_info
        if not pk:
            raise RuntimeError(f"Column {col.name} has no pk_info but is PK")

        inner = [col.type_str]
        if pk.kind == "sequence":
            # todo поправить генерацию: отдельный сиквенс плюс проставление в server_default
            inner.append(f'Sequence("{pk.seq_name}", schema="{pk.seq_schema}")')
        elif pk.kind == "identity":
            id_args = []
            if pk.identity_always is not None:
                id_args.append(f"always={pk.identity_always}")
            if pk.identity_start is not None:
                id_args.append(f"start={pk.identity_start}")
            if pk.identity_increment is not None:
                id_args.append(f"increment={pk.identity_increment}")
            if pk.identity_minvalue is not None:
                id_args.append(f"minvalue={pk.identity_minvalue}")
            if pk.identity_maxvalue is not None:
                id_args.append(f"maxvalue={pk.identity_maxvalue}")
            inner.append(f"Identity({', '.join(id_args)})")
        if col.fk_dict:
            inner.append(_fk_expr(col.fk_dict, schema))
        inner.append("primary_key=True")
        if pk.kind == "sequence":
            inner.append("autoincrement=True")
        inner.append("init=False")
        return f"    {col.name}: Mapped[{hint}] = mapped_column({', '.join(inner)})"

    if col.fk_dict:
        annotation = f"Mapped[{hint} | None]" if col.nullable else f"Mapped[{hint}]"
        extra: list[str] = []
        if col.server_default_expr:
            extra.append(f"server_default={col.server_default_expr}")
            extra.append(f"default={col.python_default_expr}")
        elif col.nullable:
            extra.append("default=None")
        lines = [f"    {col.name}: {annotation} = mapped_column("]
        lines.append(f"        {col.type_str},")
        lines.append(f"        {_fk_expr(col.fk_dict, schema)},")
        for kw in extra:
            lines.append(f"        {kw},")
        lines.append("    )")
        return "\n".join(lines)

    if col.server_default_expr:
        annotation = f"Mapped[{hint} | None]" if col.nullable else f"Mapped[{hint}]"
        lines = [
            f"    {col.name}: {annotation} = mapped_column(",
            f"        {col.type_str},",
            f"        server_default={col.server_default_expr},",
            f"        default={col.python_default_expr},",
            "    )",
        ]
        return "\n".join(lines)
    if col.nullable:
        annotation = f"Mapped[{hint} | None]"
        return f"    {col.name}: {annotation} = mapped_column({col.type_str}, default=None)"
    return f"    {col.name}: Mapped[{hint}] = mapped_column({col.type_str})"


def render_relationship(rel: RelInfo) -> str:
    target = rel.target_class

    if rel.is_list:
        annotation = f'Mapped[list["{target}"]]'
    elif rel.nullable:
        annotation = f'Mapped["{target} | None"]'
    else:
        annotation = f'Mapped["{target}"]'

    kwargs: list[str] = [f'"{target}"']
    if rel.foreign_keys_col:
        # Родительская сторона ссылается на дочернюю колонку как ``Class.col`` —
        # дочерний класс доступен лишь под TYPE_CHECKING, поэтому нужна строковая ссылка.
        if "." in rel.foreign_keys_col:
            kwargs.append(f'foreign_keys="{rel.foreign_keys_col}"')
        else:
            kwargs.append(f"foreign_keys=[{rel.foreign_keys_col}]")
    if rel.is_self_ref and not rel.is_list and rel.remote_side_col:
        kwargs.append(f"remote_side=[{rel.remote_side_col}]")
    if not rel.is_external:
        kwargs.append(f'back_populates="{rel.back_populates}"')
    kwargs.append("init=False")

    result = f"    {rel.attr_name}: {annotation} = relationship({', '.join(kwargs)})"
    if rel.todo_comment:
        result += f"  {rel.todo_comment}"
    return result


def render_model_file(
    tinfo: TableInfo,
    schema: str,
    base_class: str,
    rels: list[RelInfo],
    schema_module: str,
) -> str:
    table_name = tinfo.table_name
    class_name = pascal_case(table_name)

    ordered_cols = order_columns(classify_columns(tinfo, schema))
    pk_cols = tinfo.pk_constraint.get("constrained_columns", [])
    has_pk = bool(pk_cols)

    sa_core: set[str] = set()
    sa_orm: set[str] = {"Mapped", "mapped_column"}
    sa_dialect: set[str] = set()
    dt_types: set[str] = set()
    need_decimal = False
    need_any = False
    need_tc = bool(rels)

    for col in ordered_cols:
        ts = col.type_str.split("#")[0].strip()
        for name in ("BigInteger", "SmallInteger", "Integer"):
            if ts == name:
                sa_core.add(name)
        if ts.startswith("String"):
            sa_core.add("String")
        if ts == "Text":
            sa_core.add("Text")
        if ts.startswith("DateTime"):
            sa_core.add("DateTime")
            dt_types.add("datetime")
        if ts == "Date":
            sa_core.add("Date")
            dt_types.add("date")
        if ts == "Time":
            sa_core.add("Time")
            dt_types.add("time")
        if ts == "Boolean":
            sa_core.add("Boolean")
        if ts == "REAL":
            sa_core.add("REAL")
        if ts.startswith("Numeric"):
            sa_core.add("Numeric")
            need_decimal = True
        if ts == "JSONB":
            sa_dialect.add("JSONB")
            need_any = True
        if ts == "Text  # TODO: check type":
            sa_core.add("Text")

        if col.is_pk:
            if not col.pk_info:
                raise RuntimeError(f"Column {col.name} has no pk_info but is PK")
            if col.pk_info.kind == "sequence":
                sa_core.add("Sequence")
            elif col.pk_info.kind == "identity":
                sa_core.add("Identity")
        if col.fk_dict:
            sa_core.add("ForeignKey")
        for expr in (col.server_default_expr, col.python_default_expr):
            if expr and "text(" in expr:
                sa_core.add("text")

    if rels:
        sa_orm.add("relationship")
    if has_pk:
        sa_core.add("PrimaryKeyConstraint")
    if tinfo.check_constraints:
        sa_core.add("CheckConstraint")
    if tinfo.unique_constraints:
        sa_core.add("UniqueConstraint")
    non_unique_indexes = [idx for idx in tinfo.indexes if not idx.get("unique")]
    if non_unique_indexes:
        sa_core.add("Index")

    tc_imports: list[tuple[str, str]] = []
    for rel in rels:
        if rel.is_self_ref:
            continue
        key = (rel.target_module, rel.target_class)
        if key not in tc_imports:
            tc_imports.append(key)
    tc_imports.sort()

    lines: list[str] = []

    stdlib = []
    if dt_types:
        stdlib.append(f"from datetime import {', '.join(sorted(dt_types))}")
    if need_decimal:
        stdlib.append("from decimal import Decimal")
    typing_names = sorted((["Any"] if need_any else []) + (["TYPE_CHECKING"] if need_tc else []))
    if typing_names:
        stdlib.append(f"from typing import {', '.join(typing_names)}")
    if stdlib:
        lines.extend(stdlib)
        lines.append("")

    sa_lines = []
    if sa_core:
        sa_lines.append(f"from sqlalchemy import {', '.join(sorted(sa_core))}")
    if sa_orm:
        sa_lines.append(f"from sqlalchemy.orm import {', '.join(sorted(sa_orm))}")
    if sa_dialect:
        sa_lines.append(f"from sqlalchemy.dialects.postgresql import {', '.join(sorted(sa_dialect))}")
    if sa_lines:
        lines.extend(sa_lines)
        lines.append("")

    lines.append(f"from {schema_module} import {base_class}")

    if tc_imports:
        lines.append("")
        lines.append("if TYPE_CHECKING:")
        for mod, cls in tc_imports:
            lines.append(f"    from {mod} import {cls}")

    lines.append("")
    lines.append("")

    lines.append(f"class {class_name}({base_class}):")

    doc = [f'    """Модель {table_name}.', "", "    Поля:", ""]
    for col in ordered_cols:
        nullable_str = "nullable" if col.nullable else "not nullable"
        doc_type = col.type_str.split("#")[0].strip()
        desc = [doc_type, nullable_str]
        if col.is_pk:
            desc.append("pkey")
        if col.fk_dict:
            ref_s = col.fk_dict.get("referred_schema") or schema
            ref_t = col.fk_dict["referred_table"]
            ref_c = col.fk_dict["referred_columns"][0]
            desc.append(f"fkey -> {ref_s}.{ref_t}.{ref_c}")
        doc.append(f"    - **`{col.name}`**: {', '.join(desc)}")
    if rels:
        doc.append("")
        doc.append("    Отношения:")
        doc.append("")
        for rel in rels:
            mod_parts = rel.target_module.split(".")
            rel_path = ".".join(mod_parts[1:]) if mod_parts[0] == "models" else rel.target_module
            target = f"list[{rel_path}]" if rel.is_list else rel_path
            doc.append(f"    - **`{rel.attr_name}`**: {target}")
    doc.append('    """')
    lines.extend(doc)
    lines.append("")

    lines.append(f'    __tablename__ = "{table_name}"')

    constraint_lines: list[str] = []
    for cc in tinfo.check_constraints:
        sqltext = (cc.get("sqltext") or "").replace('"', '\\"')
        name = cc.get("name") or ""
        constraint_lines.append(f'        CheckConstraint("{sqltext}", name="{name}"),')
    if has_pk:
        pk_name = tinfo.pk_constraint.get("name") or ""
        cols_str = ", ".join(f'"{c}"' for c in pk_cols)
        constraint_lines.append(f'        PrimaryKeyConstraint({cols_str}, name="{pk_name}"),')
    for uc in tinfo.unique_constraints:
        uc_cols = ", ".join(f'"{c}"' for c in uc.get("column_names", []))
        uc_name = uc.get("name") or ""
        constraint_lines.append(f'        UniqueConstraint({uc_cols}, name="{uc_name}"),')
    for idx in non_unique_indexes:
        idx_cols = ", ".join(f'"{c}"' for c in idx.get("column_names", []))
        idx_name = idx.get("name") or ""
        constraint_lines.append(f'        Index("{idx_name}", {idx_cols}),')

    if constraint_lines:
        lines.append(f"    __table_args__ = {base_class}.with_constraints(")
        lines.extend(constraint_lines)
        lines.append("    )")

    lines.append("")

    for col in ordered_cols:
        lines.append(render_column(col, schema))

    if rels:
        lines.append("")
        for rel in rels:
            lines.append(render_relationship(rel))

    lines.append("")
    return "\n".join(lines)
