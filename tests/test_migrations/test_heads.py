"""Целостность веток миграций: ровно один head на каждый tier.

Файлы ревизий парсятся напрямую (без подключения к БД и без запуска alembic env.py,
который при импорте выполняет миграции). Ветки тиров независимы (без ``depends_on``),
поэтому head тира — это ревизия из его папки, на которую никто не ссылается как на down_revision.
"""

import re
from pathlib import Path

import pytest

from db_models.tiers import LADDER

_VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "versions"
_REVISION_RE = re.compile(r"^revision\s*[:=].*?['\"]([^'\"]+)['\"]", re.MULTILINE)
_DOWN_REVISION_RE = re.compile(r"^down_revision\s*[:=]\s*(?:['\"]([^'\"]+)['\"]|None)", re.MULTILINE)


def _heads_in_tier(tier: str) -> set[str]:
    tier_dir = _VERSIONS / tier
    revisions: set[str] = set()
    down_refs: set[str] = set()
    for py_file in tier_dir.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        rev_match = _REVISION_RE.search(text)
        assert rev_match, f"{py_file.name}: не найден revision"
        revisions.add(rev_match.group(1))
        down_match = _DOWN_REVISION_RE.search(text)
        if down_match and down_match.group(1):
            down_refs.add(down_match.group(1))
    return revisions - down_refs


@pytest.mark.parametrize("tier", [t.value for t in LADDER])
def test_single_head_per_tier(tier: str) -> None:
    heads = _heads_in_tier(tier)
    assert len(heads) == 1, f"тир {tier}: ожидался ровно один head, получено {sorted(heads)}"


def test_every_tier_has_revisions() -> None:
    for tier in (t.value for t in LADDER):
        assert (_VERSIONS / tier).is_dir(), f"нет папки ревизий для тира {tier}"
        assert any((_VERSIONS / tier).glob("*.py")), f"нет ревизий в тире {tier}"
