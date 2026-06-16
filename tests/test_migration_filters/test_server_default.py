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
        # Цельный строковый литерал: снимаем ::type и обрамляющие кавычки (БД отдаёт 'x'::type, модель — x).
        ("'x'::character varying", "x"),
        ("'x'::character varying(50)", "x"),
        ("''::timestamp without time zone", ""),
        ("'{}'::jsonb", "{}"),
        ("'new'::outboxstatus", "new"),
        ("'O''Brien'::text", "O'Brien"),
        # Внутренний "::" в литерале не пере-срезается как каст (цельный литерал распознаётся якорно).
        ("'a::b'::text", "a::b"),
        ("'a::b::c'::text", "a::b::c"),
        # Значение литерала со скобками не путается с аргументами precision у типа.
        ("'f()'::text", "f()"),
        # Каст к схемо-квалифицированному / кавыченному enum-типу тоже снимается.
        ("'new'::public.outboxstatus", "new"),
        ("'new'::\"MyEnum\"", "new"),
        ("'new'::public.\"MyEnum\"", "new"),
        # Пробелы вокруг "::" допускаются с обеих сторон.
        ("'x' :: text", "x"),
        # Конкатенация — не цельный литерал: значения не схлопываются, срезаются лишь ::type.
        ("'a'::text || 'b'::text", "'a' || 'b'"),
        # nextval/ARRAY — не цельные литералы, внутренние кавычки сохраняются.
        ("ARRAY[1, 2]::integer[]", "ARRAY[1, 2]"),
        ("nextval('seq'::regclass)", "nextval('seq')"),
        ("now()", "now()"),
        ("false", "false"),
        # Один уровень вложенных скобок в приведении не оставляет «хвоста» из ')'.
        ("'a'::some_type(one(two))", "a"),
    ],
)
def test_normalize_server_default_strips_casts(raw: str | None, expected: str | None) -> None:
    assert normalize_server_default(raw) == expected


def test_compare_server_default_numeric_cast_is_not_a_diff() -> None:
    # rendered модели = "0", БД отдаёт "0::numeric(11,2)" — значения должны считаться равными.
    assert compare_server_default(None, None, None, "0::numeric(11,2)", None, "0") is False


def test_compare_server_default_enum_quoting_is_not_a_diff() -> None:
    # БД отдаёт 'new'::outboxstatus, модель (StrEnum) рендерит new — должны считаться равными.
    assert compare_server_default(None, None, None, "'new'::outboxstatus", None, "new") is False


def test_compare_server_default_sequence_with_rendered_default_is_not_a_diff() -> None:
    # seq.next_value(): модель рендерит nextval('s'), БД — nextval('s'::regclass) — равны.
    assert (
        compare_server_default(
            None, None, None, "nextval('run_params_run_id_seq'::regclass)", None, "nextval('run_params_run_id_seq')"
        )
        is False
    )


def test_compare_server_default_detects_real_diff() -> None:
    assert compare_server_default(None, None, None, "1", None, "0") is True


def test_compare_server_default_ignores_serial_sequence() -> None:
    assert compare_server_default(None, None, None, "nextval('s'::regclass)", None, None) is False


def test_table_key() -> None:
    assert table_key("ceh", "t") == "ceh.t"
    assert table_key(None, "t") == "t"


def test_normalize_schema_name() -> None:
    assert normalize_schema_name(None) == "public"
    assert normalize_schema_name("ceh") == "ceh"
