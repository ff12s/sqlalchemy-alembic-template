#!/usr/bin/env python3
"""Scaffold a new DB schema package under db_models/models/.

Usage:
    create-schema <schema_name>

Creates ``db_models/models/<schema_name>/__init__.py`` plus a ``<tier>/__init__.py``
for every non-base tier in ``db_models.tiers.LADDER``.
"""

import re
import sys

from db_models.cli.utils import repo_root
from db_models.tiers import BASE_TIER, LADDER, Tier

REPO_ROOT = repo_root()

# Имя схемы — корректный нижнерегистровый идентификатор; tier-имена запрещены
# (совпали бы с tier-подпапками). Заодно отсекает path traversal (``../``, разделители).
SCHEMA_NAME_RE = re.compile(r"[a-z][a-z0-9_]*")
RESERVED_SCHEMA_NAMES = frozenset(t.value for t in Tier)

SCHEMA_INIT = """\
from db_models.models import Base, auto_import_models


class {class_name}(Base):
    __abstract__ = True
    _schema = "{schema_name}"


__all__ = auto_import_models(__name__, __file__, ({class_name},))
"""

# Гард tier-подпакета: модели подгружаются, только если тир активен в текущем окружении.
TIER_INIT = """\
from db_models.config import get_migration_env
from db_models.models import auto_import_models
from db_models.tiers import ENV_ALLOWED_TIERS, Tier

if Tier.{tier_const} in ENV_ALLOWED_TIERS[get_migration_env()]:
    __all__ = auto_import_models(__name__, __file__)
"""


def pascal_case(name: str) -> str:
    return "".join(w.capitalize() for w in name.split("_"))


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <schema_name>", file=sys.stderr)
        sys.exit(1)

    schema_name = sys.argv[1]
    if not SCHEMA_NAME_RE.fullmatch(schema_name) or schema_name in RESERVED_SCHEMA_NAMES:
        print(
            f"Error: invalid schema name '{schema_name}'. "
            f"Use a lowercase identifier [a-z][a-z0-9_]* that is not a tier name.",
            file=sys.stderr,
        )
        sys.exit(1)

    class_name = f"Base{pascal_case(schema_name)}"
    schema_dir = REPO_ROOT / "db_models" / "models" / schema_name

    if schema_dir.exists():
        print(f"Error: {schema_dir} already exists.", file=sys.stderr)
        sys.exit(1)

    files = {schema_dir / "__init__.py": SCHEMA_INIT.format(class_name=class_name, schema_name=schema_name)}
    for tier in LADDER:
        if tier is BASE_TIER:
            continue
        files[schema_dir / tier.value / "__init__.py"] = TIER_INIT.format(tier_const=tier.name)

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  created {path.relative_to(REPO_ROOT)}")

    print(f"\nSchema '{schema_name}' scaffolded. Base class: {class_name}")


if __name__ == "__main__":
    main()
