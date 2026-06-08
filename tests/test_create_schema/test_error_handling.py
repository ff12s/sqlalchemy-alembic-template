import sys

import pytest

import db_models.cli.create_schema as cs
from db_models.cli.create_schema import main


def test_exits_if_schema_dir_already_exists(scaffold_schema):
    scaffold_schema("my_schema")
    with pytest.raises(SystemExit):
        scaffold_schema("my_schema")


def test_exits_if_no_args(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["create_schema.py"])
    with pytest.raises(SystemExit):
        main()
