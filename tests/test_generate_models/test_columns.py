"""Тесты маппинга типов, разбора server_default и классификации PK в генераторе моделей."""

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from db_models.generate_models.columns import classify_pk_column, map_sa_type, parse_server_default


class TestMapSaType:
    def test_integer_family(self) -> None:
        assert map_sa_type(BigInteger()) == ("BigInteger", "int")
        assert map_sa_type(SmallInteger()) == ("SmallInteger", "int")
        assert map_sa_type(Integer()) == ("Integer", "int")

    def test_text_and_jsonb(self) -> None:
        assert map_sa_type(Text()) == ("Text", "str")
        assert map_sa_type(JSONB()) == ("JSONB", "dict[str, Any]")

    def test_boolean_and_date(self) -> None:
        assert map_sa_type(Boolean()) == ("Boolean", "bool")
        assert map_sa_type(Date()) == ("Date", "date")

    def test_string_length(self) -> None:
        assert map_sa_type(String(50)) == ("String(50)", "str")
        assert map_sa_type(String()) == ("String", "str")

    def test_numeric_precision(self) -> None:
        assert map_sa_type(Numeric(11, 2)) == ("Numeric(11, 2)", "Decimal")
        assert map_sa_type(Numeric()) == ("Numeric", "Decimal")

    def test_datetime_timezone_flag(self) -> None:
        assert map_sa_type(DateTime(timezone=True)) == ("DateTime(True)", "datetime")
        assert map_sa_type(DateTime()) == ("DateTime(False)", "datetime")


class TestParseServerDefault:
    def test_none_and_sequence_skip(self) -> None:
        assert parse_server_default(None) == (None, None)
        assert parse_server_default("nextval('s'::regclass)") == (None, None)

    def test_now_and_current_timestamp_are_distinct(self) -> None:
        # Регрессия: CURRENT_TIMESTAMP не должен схлопываться в now().
        assert parse_server_default("now()") == ('text("now()")', 'text("now()")')
        assert parse_server_default("CURRENT_TIMESTAMP") == (
            'text("CURRENT_TIMESTAMP")',
            'text("CURRENT_TIMESTAMP")',
        )

    def test_booleans(self) -> None:
        assert parse_server_default("false") == ('text("false")', "False")
        assert parse_server_default("true") == ('text("true")', "True")

    def test_integer(self) -> None:
        assert parse_server_default("0") == ('text("0")', "0")

    def test_varchar_literal(self) -> None:
        assert parse_server_default("'DAPP'::character varying") == ("text(\"'DAPP'\")", '"DAPP"')


class TestClassifyPkColumn:
    def test_identity(self) -> None:
        info = classify_pk_column({"identity": {"always": True, "start": 1}}, "public")
        assert info.kind == "identity"
        assert info.identity_always is True
        assert info.identity_start == 1

    def test_sequence_qualified(self) -> None:
        info = classify_pk_column({"default": "nextval('public.foo_seq'::regclass)"}, "example")
        assert info.kind == "sequence"
        assert info.seq_name == "foo_seq"
        assert info.seq_schema == "public"

    def test_sequence_unqualified_uses_table_schema(self) -> None:
        info = classify_pk_column({"default": "nextval('foo_seq'::regclass)"}, "example")
        assert info.kind == "sequence"
        assert info.seq_schema == "example"

    def test_plain(self) -> None:
        assert classify_pk_column({}, "public").kind == "plain"
