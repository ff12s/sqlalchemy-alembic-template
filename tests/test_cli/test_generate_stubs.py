from db_models.cli.generate_stubs.parsing import collect_symbols


def _symbols(tmp_path, source) -> list[str]:
    """Записывает source во временный .py и возвращает collect_symbols по нему."""
    py_file = tmp_path / "m.py"
    py_file.write_text(source, encoding="utf-8")
    return collect_symbols(py_file)


def test_collects_class_names_in_order(tmp_path):
    assert _symbols(tmp_path, "class Foo:\n    pass\n\n\nclass Bar:\n    pass\n") == ["Foo", "Bar"]


def test_collects_core_table_assignment(tmp_path):
    assert _symbols(tmp_path, 't = Table("t", meta)\n') == ["t"]


def test_collects_table_via_attribute_call(tmp_path):
    assert _symbols(tmp_path, 't = sa.Table("t", meta)\n') == ["t"]


def test_collects_annotated_table_assignment(tmp_path):
    assert _symbols(tmp_path, 't: Table = Table("t", meta)\n') == ["t"]


def test_ignores_non_table_assignments(tmp_path):
    assert _symbols(tmp_path, "X = 5\nY: int = 6\n") == []


def test_bare_annotation_without_value_is_ignored(tmp_path):
    assert _symbols(tmp_path, "x: Table\n") == []


def test_mixed_top_level_preserves_order(tmp_path):
    source = 'class Foo:\n    pass\n\n\nbar = Table("bar", meta)\n\nX = 1\n'
    assert _symbols(tmp_path, source) == ["Foo", "bar"]


def test_returns_empty_on_syntax_error(tmp_path):
    assert _symbols(tmp_path, "def (:\n") == []
