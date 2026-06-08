from db_models.models import Base, auto_import_models


class BaseExample(Base):
    __abstract__ = True
    _schema = "example"


__all__ = auto_import_models(__name__, __file__, (BaseExample,))
