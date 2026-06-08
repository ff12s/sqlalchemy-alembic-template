from collections.abc import Callable
from dataclasses import dataclass

from db_models.generate_models.reflection import TableInfo


def pascal_case(name: str) -> str:
    return "".join(w.capitalize() for w in name.split("_"))


def _unique_name(base: str, used: set[str]) -> str:
    name = base
    while name in used:
        name += "_"
    return name


@dataclass
class RelInfo:
    attr_name: str
    target_class: str
    target_module: str
    is_list: bool
    back_populates: str
    foreign_keys_col: str | None
    is_self_ref: bool
    is_external: bool
    nullable: bool = False
    remote_side_col: str | None = None
    todo_comment: str | None = None


class FKGraph:
    def __init__(self) -> None:
        self.rels: dict[str, list[RelInfo]] = {}

    @classmethod
    def build(
        cls,
        all_tables: dict[str, TableInfo],
        schema: str,
        resolve_module: Callable[[str, str], str],
    ) -> "FKGraph":
        """
        Построить граф связей по внешним ключам всех таблиц схемы.

        :param all_tables: Отрефлексированные таблицы по имени.
        :param schema: Имя схемы БД.
        :param resolve_module: Функция (схема, таблица) -> import-путь модели нужного тира.
        :return: Граф связей.
        """
        graph = cls()
        table_set = set(all_tables.keys())
        for t in table_set:
            graph.rels[t] = []

        used_names: dict[str, set[str]] = {t: set() for t in table_set}

        for child_table in sorted(all_tables.keys()):
            tinfo = all_tables[child_table]
            if not tinfo.foreign_keys:
                continue

            col_nullable = {c["name"]: c["nullable"] for c in tinfo.columns}
            pk_cols = tinfo.pk_constraint.get("constrained_columns", [])
            pk_col = pk_cols[0] if pk_cols else None

            fks_by_parent: dict[str, list[dict]] = {}
            for fk in tinfo.foreign_keys:
                ref_schema_val = fk.get("referred_schema") or schema
                parent_key = f"{ref_schema_val}.{fk['referred_table']}"
                fks_by_parent.setdefault(parent_key, []).append(fk)

            for parent_key, fks in fks_by_parent.items():
                ref_schema_val, ref_table = parent_key.split(".", 1)
                is_self_ref = ref_table == child_table and ref_schema_val == schema
                is_external = ref_table not in table_set or ref_schema_val != schema
                is_multi_fk = len(fks) > 1

                parent_class = pascal_case(ref_table)
                parent_module = resolve_module(ref_schema_val, ref_table)
                child_class = pascal_case(child_table)
                child_module = resolve_module(schema, child_table)

                for fk in fks:
                    fk_col = fk["constrained_columns"][0] if fk["constrained_columns"] else None
                    is_fk_nullable = col_nullable.get(fk_col, True) if fk_col else True

                    if is_multi_fk:
                        child_attr_base = fk_col[:-3] if fk_col and fk_col.endswith("_id") else fk_col or ref_table
                        child_fk_disambig = fk_col
                        parent_fk_disambig = f"{child_class}.{fk_col}" if fk_col else None
                    else:
                        child_attr_base = ref_table
                        child_fk_disambig = parent_fk_disambig = None

                    child_attr = _unique_name(child_attr_base, used_names[child_table])
                    used_names[child_table].add(child_attr)

                    parent_attr_base = child_table + "_list" if child_table.endswith("s") else child_table + "s"

                    if not is_external:
                        parent_attr = _unique_name(parent_attr_base, used_names.get(ref_table, set()))
                        used_names.setdefault(ref_table, set()).add(parent_attr)
                    else:
                        parent_attr = parent_attr_base

                    child_rel = RelInfo(
                        attr_name=child_attr,
                        target_class=parent_class,
                        target_module=parent_module,
                        is_list=False,
                        back_populates=parent_attr,
                        foreign_keys_col=child_fk_disambig,
                        is_self_ref=is_self_ref,
                        is_external=is_external,
                        nullable=is_fk_nullable,
                        remote_side_col=pk_col if is_self_ref else None,
                        todo_comment=(
                            f"# TODO: add back_populates to {ref_schema_val}.{ref_table}" if is_external else None
                        ),
                    )
                    graph.rels[child_table].append(child_rel)

                    if not is_external:
                        parent_rel = RelInfo(
                            attr_name=parent_attr,
                            target_class=child_class,
                            target_module=child_module,
                            is_list=True,
                            back_populates=child_attr,
                            foreign_keys_col=parent_fk_disambig,
                            is_self_ref=is_self_ref,
                            is_external=False,
                        )
                        graph.rels.setdefault(ref_table, []).append(parent_rel)

        return graph
