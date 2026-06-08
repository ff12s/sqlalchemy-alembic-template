"""Команда ``generate-stubs``: генерация ``__init__.pyi`` стабов базового тира для всех схем.

Для каждой схемы AST-парсит файлы базового тира (верхний уровень, без tier-подпапок)
и создаёт ``__init__.pyi`` с ре-экспортами классов и Core ``Table``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from db_models.cli.generate_stubs.parsing import collect_symbols, find_base_class
from db_models.cli.utils import repo_root
from db_models.tiers import LADDER

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["main"]

ROOT = repo_root()
MODELS_DIR = ROOT / "db_models" / "models"
TIER_SUBDIRS = {t.value for t in LADDER}


def generate_schema_stub(schema_dir: Path) -> None:
    """Сгенерировать ``__init__.pyi`` для одной схемы из её файлов базового тира.

    :param schema_dir: Каталог пакета схемы (уровень базового тира).
    """
    package = f"db_models.models.{schema_dir.name}"

    base_class_name = find_base_class(schema_dir / "__init__.py")

    # (symbol, module_stem) — только файлы базового тира
    entries: list[tuple[str, str]] = []
    for py_file in sorted(schema_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        if py_file.stem in TIER_SUBDIRS:
            continue
        for name in collect_symbols(py_file):
            entries.append((name, py_file.stem))

    if not entries and not base_class_name:
        return

    # Импорты идут до объявления класса, чтобы стаб не нарушал E402.
    lines: list[str] = ["# Сгенерировано generate-stubs — не редактировать вручную."]
    if base_class_name:
        lines.append("from db_models.models import Base as Base")
    lines.extend(f"from {package}.{stem} import {name} as {name}" for name, stem in sorted(entries))
    if base_class_name:
        lines.append("")
        lines.append(f"class {base_class_name}(Base): ...")

    stub_path = schema_dir / "__init__.pyi"
    stub_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  updated {stub_path.relative_to(ROOT)}")


def main() -> None:
    """Перегенерировать ``__init__.pyi`` стабы базового тира для всех схем."""
    schemas = sorted(p for p in MODELS_DIR.iterdir() if p.is_dir() and not p.name.startswith("_"))
    for schema_dir in schemas:
        generate_schema_stub(schema_dir)
