import os
from urllib.parse import quote_plus

from db_models.tiers import BASE_TIER, Tier

ALLOWED_MIGRATION_ENVS: frozenset[Tier] = frozenset(Tier)
DEFAULT_DATABASE_BY_ENV: dict[Tier, str] = {t: t.value for t in Tier}


def get_migration_env(default: Tier = BASE_TIER) -> Tier:
    """Read MIGRATION_ENV and return the corresponding Tier, falling back to `default`."""
    raw = os.getenv("MIGRATION_ENV", "").strip().lower()
    if not raw:
        return default
    try:
        return Tier(raw)
    except ValueError:
        return default


def database_name_for(tier: Tier) -> str:
    """
    Определить имя БД для тира: ``DATABASE_NAME`` имеет приоритет, иначе дефолт тира.

    :param tier: Тир, к БД которого выполняется подключение.
    :return: Имя базы данных.
    """
    database_name = os.getenv("DATABASE_NAME")
    if database_name:
        return database_name

    return DEFAULT_DATABASE_BY_ENV[tier]


def database_uri_for(tier: Tier) -> str:
    """
    Построить URI подключения к БД указанного тира.

    :param tier: Тир, к БД которого выполняется подключение.
    :return: Строка подключения SQLAlchemy.
    """
    return "postgresql+psycopg://{user}:{password}@{host}:{port}/{database}".format(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=os.getenv("DATABASE_PORT", "5432"),
        database=database_name_for(tier),
        user=os.getenv("DATABASE_USER", "postgres"),
        password=quote_plus(os.getenv("DATABASE_PASSWORD", "postgres")),
    )


SQLALCHEMY_DATABASE_URI: str = database_uri_for(get_migration_env())
