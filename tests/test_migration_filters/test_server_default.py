import pytest

from migrations.migration_filters import (
    compare_server_default,
    normalize_schema_name,
    normalize_server_default,
    table_key,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("0", "0"),
        # Регрессия: ::numeric(11,2) раньше превращался в "0(11,2)" и давал вечный шумовой diff.
        ("0::numeric(11,2)", "0"),
        ("0::numeric", "0"),
        ("'x'::character varying", "'x'"),
        ("'x'::character varying(50)", "'x'"),
        ("''::timestamp without time zone", "''"),
        ("'{}'::jsonb", "'{}'"),
        ("ARRAY[1, 2]::integer[]", "ARRAY[1, 2]"),
        ("nextval('seq'::regclass)", "nextval('seq')"),
        ("now()", "now()"),
        ("false", "false"),
        # Один уровень вложенных скобок в приведении не оставляет «хвоста» из ')'.
        ("'a'::some_type(one(two))", "'a'"),
    ],
)
def test_normalize_server_default_strips_casts(raw: str | None, expected: str | None) -> None:
    assert normalize_server_default(raw) == expected


def test_compare_server_default_numeric_cast_is_not_a_diff() -> None:
    # rendered модели = "0", БД отдаёт "0::numeric(11,2)" — значения должны считаться равными.
    assert compare_server_default(None, None, None, "0::numeric(11,2)", None, "0") is False


def test_compare_server_default_detects_real_diff() -> None:
    assert compare_server_default(None, None, None, "1", None, "0") is True


def test_compare_server_default_ignores_serial_sequence() -> None:
    assert compare_server_default(None, None, None, "nextval('s'::regclass)", None, None) is False


def test_table_key() -> None:
    assert table_key("example", "t") == "example.t"
    assert table_key(None, "t") == "t"


def test_normalize_schema_name() -> None:
    assert normalize_schema_name(None) == "public"
    assert normalize_schema_name("example") == "example"
