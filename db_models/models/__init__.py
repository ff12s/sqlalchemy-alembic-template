import importlib
import pkgutil
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import ClassVar

from sqlalchemy import Table as SATable
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, declared_attr
from sqlalchemy.schema import SchemaItem

from db_models.config import get_migration_env
from db_models.tiers import BASE_TIER, ENV_ALLOWED_TIERS, LADDER, Tier, tier_of_module

try:
    __version__ = _pkg_version("db-models-template")
except PackageNotFoundError:  # запуск из исходников без установки пакета
    __version__ = "0.0.0+unknown"


class Base(MappedAsDataclass, DeclarativeBase):
    __abstract__ = True
    _schema: ClassVar[str | None] = None

    @declared_attr.directive
    def __table_args__(cls) -> tuple[dict[str, str], ...]:
        return ({"schema": cls._schema},) if cls._schema else tuple()

    @classmethod
    def with_constraints(cls, *constraints: SchemaItem) -> tuple[SchemaItem | dict[str, str], ...]:
        return constraints + ({"schema": cls._schema},) if cls._schema else constraints


def _collect_override_stems(package_dir: Path) -> set[str]:
    """Возвращает stems main-файлов, у которых есть tier-специфичный override.

    Подпапки тиров обходятся в порядке LADDER, поэтому при одинаковом stem
    в нескольких подпапках побеждает самый специфичный тир.
    """

    current_env = get_migration_env()
    active_non_base = ENV_ALLOWED_TIERS[current_env] - {BASE_TIER}

    override_stems: set[str] = set()
    for tier in LADDER:
        if tier not in active_non_base:
            continue
        subdir = package_dir / tier.value
        if not subdir.is_dir():
            continue
        for py_file in subdir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            override_stems.add(py_file.stem)

    return override_stems


def _shadowed_stems(package_dir: Path) -> set[str]:
    """Возвращает stems, которые tier-подпакет НЕ должен импортировать.

    Файл затеняется, если более специфичный активный тир содержит файл с тем же
    stem (реализация правила «побеждает самый специфичный тир» на уровне импорта).
    Для не-tier пакетов (main-уровень) всегда возвращает пустое множество.

    :param package_dir: каталог импортируемого пакета (tier-подпапка или main-уровень)
    :return: множество stems, импорт которых нужно пропустить
    """
    try:
        own_tier = Tier(package_dir.name)
    except ValueError:
        return set()

    active_tiers = ENV_ALLOWED_TIERS[get_migration_env()]
    more_specific = LADDER[LADDER.index(own_tier) + 1 :]
    parent_dir = package_dir.parent

    shadowed: set[str] = set()
    for tier in more_specific:
        if tier not in active_tiers:
            continue
        subdir = parent_dir / tier.value
        if not subdir.is_dir():
            continue
        for py_file in subdir.glob("*.py"):
            if py_file.name != "__init__.py":
                shadowed.add(py_file.stem)

    return shadowed


def auto_import_models(
    package_name: str,
    package_file: str,
    exclude_classes: Sequence[type] = (),
) -> list[str]:
    """
    Автоматически импортирует все модели из пакета с учётом tier-override.

    Для main-модуля с одноимённым файлом в активной tier-подпапке (dev/)
    main-версия пропускается; побеждает самый специфичный тир (dev > main).

    Args:
        package_name: имя пакета (__name__)
        package_file: путь к __init__.py (__file__)
        exclude_classes: классы, которые нужно исключить из экспорта

    Returns:
        Список имён импортированных моделей для __all__
    """
    package_dir = Path(package_file).parent
    caller_globals = importlib.import_module(package_name).__dict__
    exported: list[str] = []
    seen: set[str] = set()

    skip_stems = _collect_override_stems(package_dir) | _shadowed_stems(package_dir)

    for _, module_name, is_pkg in pkgutil.iter_modules([str(package_dir)]):
        if not is_pkg and module_name in skip_stems:
            continue
        module = importlib.import_module(f".{module_name}", package_name)
        if is_pkg:
            for attr_name in getattr(module, "__all__", []):
                if attr_name in seen:
                    continue
                seen.add(attr_name)
                caller_globals[attr_name] = getattr(module, attr_name)
                exported.append(attr_name)
        else:
            tier = tier_of_module(f"{package_name}.{module_name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Base)
                    and attr is not Base
                    and not attr.__dict__.get("__abstract__", False)
                    and attr not in exclude_classes
                ):
                    if attr_name in seen:
                        continue
                    seen.add(attr_name)
                    caller_globals[attr_name] = attr
                    exported.append(attr_name)
                elif isinstance(attr, SATable) and attr.metadata is Base.metadata:
                    attr.info.setdefault("migration_tier", tier)

    return exported


__all__ = auto_import_models(__name__, __file__)
