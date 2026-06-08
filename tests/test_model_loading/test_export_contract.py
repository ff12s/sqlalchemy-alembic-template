"""Контракт публичного API ``db_models.models.__all__``.

Загрузка делается в подпроцессе с ``MIGRATION_ENV=dev`` — это самый широкий контур
(видит все тиры), и именно в нём раньше протекали абстрактные базы и дубликаты.
Подпроцесс изолирует глобальный registry SQLAlchemy от остальной сессии.
"""

import json
import os
import subprocess
import sys
from typing import Any

_CHECK = """
import json
import db_models.models as m

names = list(m.__all__)
seen = set()
dups = sorted({n for n in names if n in seen or seen.add(n)})

abstract = []
for n in names:
    obj = getattr(m, n, None)
    if isinstance(obj, type) and obj.__dict__.get("__abstract__", False):
        abstract.append(n)

print("RESULT:" + json.dumps({"dups": dups, "abstract": abstract, "count": len(names)}))
"""


def _load_export_contract(tier: str) -> dict[str, Any]:
    env = dict(os.environ)
    env["MIGRATION_ENV"] = tier
    proc = subprocess.run(  # noqa: S603  фиксированная команда: интерпретатор сессии + статический скрипт
        [sys.executable, "-c", _CHECK],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT:"))
    return json.loads(line[len("RESULT:") :])


def test_dev_env_all_has_no_duplicates() -> None:
    data = _load_export_contract("dev")
    assert data["dups"] == [], f"в __all__ есть дубликаты: {data['dups']}"


def test_dev_env_all_excludes_abstract_bases() -> None:
    data = _load_export_contract("dev")
    assert data["abstract"] == [], f"в __all__ протекли абстрактные базы: {data['abstract']}"


def test_dev_env_exports_models() -> None:
    data = _load_export_contract("dev")
    assert data["count"] > 0
