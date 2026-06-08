"""AST-извлечение имён классов и Core ``Table`` из top-level файла модели схемы."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def is_table_call(node: ast.expr) -> bool:
    """Вернуть ``True``, если узел — вызов ``Table(...)`` или ``<mod>.Table(...)``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "Table") or (
        isinstance(func, ast.Attribute) and func.attr == "Table"
    )


def node_symbols(stmt: ast.stmt) -> list[str]:
    """Имена класса или Core Table-переменных, объявленных одним top-level узлом."""
    if isinstance(stmt, ast.ClassDef):
        return [stmt.name]
    if isinstance(stmt, ast.Assign) and is_table_call(stmt.value):
        return [target.id for target in stmt.targets if isinstance(target, ast.Name)]
    if (
        isinstance(stmt, ast.AnnAssign)
        and stmt.value
        and is_table_call(stmt.value)
        and isinstance(stmt.target, ast.Name)
    ):
        return [stmt.target.id]
    return []


def collect_symbols(py_file: Path) -> list[str]:
    """Вернуть имена классов и Core ``Table`` из файла (только top-level).

    :param py_file: Путь к файлу модели.
    :return: Имена в порядке объявления; пустой список при ошибке разбора.
    """
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    return [name for stmt in tree.body for name in node_symbols(stmt)]


def find_base_class(init_py: Path) -> str | None:
    """Вернуть имя ``Base``-подкласса, объявленного в ``__init__.py`` схемы.

    :param init_py: Путь к ``__init__.py`` пакета схемы.
    :return: Имя класса либо ``None``.
    """
    try:
        tree = ast.parse(init_py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef):
            for base in stmt.bases:
                if isinstance(base, ast.Name) and base.id == "Base":
                    return stmt.name
    return None
