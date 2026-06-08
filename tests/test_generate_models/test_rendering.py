"""Тесты рендеринга колонок: аннотации, init=False для PK, многострочный server_default."""

import ast

from db_models.generate_models.columns import ColumnData, PKInfo
from db_models.generate_models.rendering import render_column


def _col(**overrides: object) -> ColumnData:
    base: dict[str, object] = {
        "name": "x",
        "type_str": "Integer",
        "python_hint": "int",
        "nullable": False,
        "is_pk": False,
        "pk_info": None,
        "fk_dict": None,
        "server_default_expr": None,
        "python_default_expr": None,
        "category": "required",
    }
    base.update(overrides)
    return ColumnData(**base)


def _is_valid_python(line: str) -> bool:
    # Колонка — присваивание в теле класса; оборачиваем в class, чтобы распарсить.
    src = "class _T:\n" + "\n".join("    " + ln for ln in line.splitlines())
    try:
        ast.parse(src)
    except SyntaxError:
        return False
    return True


def test_plain_required() -> None:
    out = render_column(_col(name="qty", type_str="Integer", python_hint="int"), "public")
    assert out == "    qty: Mapped[int] = mapped_column(Integer)"
    assert _is_valid_python(out)


def test_nullable_gets_default_none() -> None:
    out = render_column(
        _col(name="note", type_str="Text", python_hint="str", nullable=True, category="nullable"), "public"
    )
    assert out == "    note: Mapped[str | None] = mapped_column(Text, default=None)"
    assert _is_valid_python(out)


def test_server_default_is_multiline_and_within_line_length() -> None:
    out = render_column(
        _col(
            name="created_at",
            type_str="DateTime(True)",
            python_hint="datetime",
            server_default_expr='text("CURRENT_TIMESTAMP")',
            python_default_expr='text("CURRENT_TIMESTAMP")',
            category="server_default",
        ),
        "public",
    )
    assert 'server_default=text("CURRENT_TIMESTAMP"),' in out
    assert out.count("\n") >= 3
    assert all(len(line) <= 120 for line in out.splitlines())
    assert _is_valid_python(out)


def test_pk_sequence_is_init_false_with_sequence() -> None:
    out = render_column(
        _col(
            name="id",
            type_str="Integer",
            python_hint="int",
            is_pk=True,
            pk_info=PKInfo(kind="sequence", seq_name="foo_seq", seq_schema="public"),
            category="pk",
        ),
        "public",
    )
    assert "primary_key=True" in out
    assert "init=False" in out
    assert 'Sequence("foo_seq", schema="public")' in out
    assert _is_valid_python(out)


def test_pk_identity() -> None:
    out = render_column(
        _col(
            name="id",
            is_pk=True,
            pk_info=PKInfo(kind="identity", identity_always=True, identity_start=1),
            category="pk",
        ),
        "public",
    )
    assert "Identity(always=True, start=1)" in out
    assert "init=False" in out
    assert _is_valid_python(out)
