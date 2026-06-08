from db_models.config import get_migration_env
from db_models.models import auto_import_models
from db_models.tiers import ENV_ALLOWED_TIERS, Tier

if Tier.DEV in ENV_ALLOWED_TIERS[get_migration_env()]:
    __all__ = auto_import_models(__name__, __file__)
