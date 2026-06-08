import ast

import pytest

# ── schema __init__.py ────────────────────────────────────────────────────────


def test_schema_init_contains_class_name(scaffold_schema, tmp_path):
    scaffold_schema("data_quality")
    content = (tmp_path / "db_models" / "models" / "data_quality" / "__init__.py").read_text()
    assert "BaseDataQuality" in content


def test_schema_init_contains_schema_name(scaffold_schema, tmp_path):
    scaffold_schema("data_quality")
    content = (tmp_path / "db_models" / "models" / "data_quality" / "__init__.py").read_text()
    assert '_schema = "data_quality"' in content


def test_schema_init_excludes_base_class_from_auto_import(scaffold_schema, tmp_path):
    scaffold_schema("my_schema")
    content = (tmp_path / "db_models" / "models" / "my_schema" / "__init__.py").read_text()
    assert "auto_import_models(__name__, __file__, (BaseMySchema,))" in content


# ── tier __init__.py ──────────────────────────────────────────────────────────


def test_dev_init_checks_dev_tier(scaffold_schema, tmp_path):
    scaffold_schema("my_schema")
    content = (tmp_path / "db_models" / "models" / "my_schema" / "dev" / "__init__.py").read_text()
    assert "Tier.DEV in ENV_ALLOWED_TIERS[get_migration_env()]" in content


# ── valid Python ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("rel_path", ["__init__.py", "dev/__init__.py"])
def test_generated_file_is_valid_python(scaffold_schema, tmp_path, rel_path):
    scaffold_schema("my_schema")
    source = (tmp_path / "db_models" / "models" / "my_schema" / rel_path).read_text()
    ast.parse(source)
