def test_creates_schema_init(scaffold_schema, tmp_path):
    scaffold_schema("my_schema")
    assert (tmp_path / "db_models" / "models" / "my_schema" / "__init__.py").exists()


def test_creates_dev_init(scaffold_schema, tmp_path):
    scaffold_schema("my_schema")
    assert (tmp_path / "db_models" / "models" / "my_schema" / "dev" / "__init__.py").exists()


def test_does_not_create_non_ladder_tier_dirs(scaffold_schema, tmp_path):
    # На лестнице (main, dev) единственный non-base тир — dev: папки ift/preprod не создаются.
    scaffold_schema("my_schema")
    base = tmp_path / "db_models" / "models" / "my_schema"
    assert not (base / "ift").exists()
    assert not (base / "preprod").exists()
    assert not (base / "main").exists()
