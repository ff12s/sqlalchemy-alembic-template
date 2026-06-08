from enum import StrEnum


class Tier(StrEnum):
    MAIN = "main"
    DEV = "dev"

    def __str__(self) -> str:
        return self.value


# Лестница тиров: каждый тир «содержит» себя и все нижестоящие. Единственный источник
# правды о наборе и порядке тиров — остальной код берёт тиры только отсюда.
LADDER: tuple[Tier, ...] = (Tier.MAIN, Tier.DEV)

# Базовый (самый широкий) тир — вершина лестницы, присутствует в любом окружении.
BASE_TIER: Tier = LADDER[0]

ENV_ALLOWED_TIERS: dict[Tier, frozenset[Tier]] = {t: frozenset(LADDER[: i + 1]) for i, t in enumerate(LADDER)}


def tier_of_module(module_name: str) -> Tier:
    """Определяет tier модели по её import-пути: побеждает самый специфичный сегмент.

    Тир берётся только из сегмента-папки, а не из имени самого модуля: файл
    ``db_models.models.example.dev`` (``example/dev.py``) — это модель базового тира,
    а не dev-тира.

    :param module_name: полный import-путь модуля (например ``db_models.models.example.dev.bar``)
    :return: tier, в подпапке которого лежит модуль, либо ``BASE_TIER`` при отсутствии tier-сегмента
    """
    parent_parts = set(module_name.split(".")[:-1])
    for tier in reversed(LADDER):
        if tier is not BASE_TIER and tier in parent_parts:
            return tier
    return BASE_TIER
