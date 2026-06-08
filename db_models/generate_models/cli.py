import argparse

from db_models.models import BASE_TIER, Tier

_TIER_CHOICES = ", ".join(t.value for t in Tier)
_TIER_METAVAR = "{" + ",".join(t.value for t in Tier) + "}"


def _tier(value: str) -> Tier:
    """
    Преобразовать строку в значение тира.

    :param value: Имя тира из командной строки.
    :return: Соответствующий элемент :class:`Tier`.
    :raises argparse.ArgumentTypeError: Если тир неизвестен.
    """
    try:
        return Tier(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"неизвестный тир '{value}' (допустимо: {_TIER_CHOICES})") from None


def _tables(value: str) -> list[str]:
    """
    Разобрать значение --tables в список имён таблиц.

    :param value: Строка с именами таблиц через запятую.
    :return: Список непустых имён таблиц.
    """
    return [t.strip() for t in value.split(",") if t.strip()]


def parse_args() -> tuple[str, Tier, list[str] | None, bool]:
    """
    Разобрать аргументы командной строки генератора моделей.

    :return: Кортеж (схема, тир, фильтр таблиц или None, флаг перезаписи).
    """
    parser = argparse.ArgumentParser(
        prog="generate_models",
        description="Сгенерировать ORM-модели из таблиц схемы живой БД.",
    )
    parser.add_argument("schema", help="имя схемы БД")
    parser.add_argument(
        "tier",
        nargs="?",
        type=_tier,
        default=BASE_TIER,
        metavar=_TIER_METAVAR,
        help=f"тир модели (по умолчанию {BASE_TIER.value})",
    )
    parser.add_argument(
        "--tables",
        type=_tables,
        default=None,
        metavar="t1,t2",
        help="генерировать только указанные таблицы",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="перезаписать существующие файлы моделей",
    )

    args = parser.parse_args()
    return args.schema, args.tier, args.tables, args.overwrite
