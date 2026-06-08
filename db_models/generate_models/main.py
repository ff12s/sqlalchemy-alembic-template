import sys
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import create_engine, inspect

from db_models import config
from db_models.generate_models.cli import parse_args
from db_models.generate_models.reflection import REPO_ROOT, discover_schema_package, reflect_table
from db_models.generate_models.relationships import FKGraph
from db_models.generate_models.rendering import render_model_file
from db_models.models import Tier
from db_models.tiers import BASE_TIER, ENV_ALLOWED_TIERS, LADDER


def _tier_dir(schema_dir: Path, tier: Tier) -> Path:
    """
    Вернуть каталог с моделями указанного тира внутри пакета схемы.

    :param schema_dir: Каталог пакета схемы (уровень базового тира).
    :param tier: Тир, чей каталог нужен.
    :return: Каталог самой схемы для базового тира, иначе подпапку тира.
    """
    return schema_dir if tier == BASE_TIER else schema_dir / tier


def _existing_model_tier(schema_dir: Path, table_name: str, target: Tier) -> Tier | None:
    """
    Найти тир, в котором уже определена модель таблицы и который виден целевому тиру.

    Перебор идёт от самого общего тира (базового) к самому частному, поэтому
    возвращается наиболее общее определение, покрывающее ``target``.

    :param schema_dir: Каталог пакета схемы.
    :param table_name: Имя таблицы (без расширения).
    :param target: Тир, для которого выполняется генерация.
    :return: Тир с существующей моделью либо ``None``, если её нет.
    """
    for tier in LADDER:
        if tier not in ENV_ALLOWED_TIERS[target]:
            continue
        if (_tier_dir(schema_dir, tier) / f"{table_name}.py").exists():
            return tier
    return None


def _module_path(schema: str, tier: Tier, table_name: str) -> str:
    """
    Собрать import-путь модели для таблицы в указанном тире.

    :param schema: Имя схемы БД.
    :param tier: Тир, в подпапке которого лежит модель (базовый — в корне схемы).
    :param table_name: Имя таблицы (без расширения).
    :return: Полный import-путь модуля модели.
    """
    if tier == BASE_TIER:
        return f"db_models.models.{schema}.{table_name}"
    return f"db_models.models.{schema}.{tier}.{table_name}"


def _make_module_resolver(schema: str, target: Tier, pending: set[str]) -> Callable[[str, str], str]:
    """
    Создать функцию выбора import-пути связанной модели для текущего тира.

    Путь указывает на самую специфичную модель, видимую тиру ``target``: сначала
    ищется существующий файл (от частного тира к общему), затем — таблица,
    создаваемая в этом же запуске; иначе используется путь базового тира.

    :param schema: Схема генерируемых моделей.
    :param target: Тир, для которого выполняется генерация.
    :param pending: Таблицы ``schema``, создаваемые в этом запуске в тире ``target``.
    :return: Функция (схема, таблица) -> import-путь.
    """

    def resolve(ref_schema: str, ref_table: str) -> str:
        ref_dir = REPO_ROOT / "models" / ref_schema
        for tier in reversed(LADDER):
            if tier not in ENV_ALLOWED_TIERS[target]:
                continue
            if (_tier_dir(ref_dir, tier) / f"{ref_table}.py").exists():
                return _module_path(ref_schema, tier, ref_table)
        if ref_schema == schema and ref_table in pending:
            return _module_path(ref_schema, target, ref_table)
        return f"db_models.models.{ref_schema}.{ref_table}"

    return resolve


def main() -> None:
    schema, tier, tables_filter, overwrite = parse_args()
    schema_dir, base_class = discover_schema_package(schema)

    print(f"Подключение к БД тира {tier} ({config.database_name_for(tier)})")
    engine = create_engine(config.database_uri_for(tier))
    inspector = inspect(engine)

    available = inspector.get_table_names(schema=schema)
    if not available:
        print(f"Warning: no tables found in schema '{schema}'")
        engine.dispose()
        return

    if tables_filter is not None:
        missing = sorted(set(tables_filter) - set(available))
        if missing:
            print(
                f"Error: tables not found in schema '{schema}': {', '.join(missing)}",
                file=sys.stderr,
            )
            engine.dispose()
            sys.exit(1)
        tables = tables_filter
    else:
        tables = sorted(available)

    all_table_infos = {t: reflect_table(inspector, t, schema) for t in tables}
    fk_graph = FKGraph.build(all_table_infos, schema, _make_module_resolver(schema, tier, set(tables)))

    schema_module = f"db_models.models.{schema}"
    output_dir = _tier_dir(schema_dir, tier)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = skipped = 0
    for table_name in sorted(tables):
        existing_tier = _existing_model_tier(schema_dir, table_name, tier)
        if existing_tier is not None and existing_tier != tier:
            print(f"  skipped (определена в тире {existing_tier}): {table_name}")
            skipped += 1
            continue

        out_file = output_dir / f"{table_name}.py"
        if out_file.exists() and not overwrite:
            print(f"  skipped (exists): {out_file.relative_to(REPO_ROOT)}")
            skipped += 1
            continue

        content = render_model_file(
            all_table_infos[table_name],
            schema,
            base_class,
            fk_graph.rels.get(table_name, []),
            schema_module,
        )
        out_file.write_text(content, encoding="utf-8")
        print(f"  generated: {out_file.relative_to(REPO_ROOT)}")
        generated += 1

    engine.dispose()
    print(f"\nDone: {generated} generated, {skipped} skipped.")
