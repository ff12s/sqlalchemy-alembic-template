import sys

import pytest

import db_models.cli.create_schema as cs
from db_models.cli.create_schema import main


@pytest.fixture
def scaffold_schema(tmp_path, monkeypatch):
    """Запускает create_schema main() с REPO_ROOT, перенаправленным в tmp_path.

    :return: callable scaffold_schema(schema_name) -> None.
    """
    monkeypatch.setattr(cs, "REPO_ROOT", tmp_path)

    def _run(schema_name: str) -> None:
        monkeypatch.setattr(sys, "argv", ["create_schema.py", schema_name])
        main()

    return _run
