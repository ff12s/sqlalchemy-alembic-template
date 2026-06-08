from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Identity, Integer, PrimaryKeyConstraint, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.models.example import BaseExample

if TYPE_CHECKING:
    from db_models.models.example.bar import Bar


class Foo(BaseExample):
    """Пример родительской модели.

    Поля:
        - **`foo_id`**: Integer, not nullable, pkey
        - **`name`**: String(100), not nullable
        - **`created_at`**: DateTime(True), not nullable

    Отношения:
        - **`bars`**: list[db_models.models.example.bar.Bar]
    """

    __tablename__ = "foo"
    __table_args__ = BaseExample.with_constraints(
        PrimaryKeyConstraint("foo_id", name="foo_pkey"),
        UniqueConstraint("name", name="foo_name_uk"),
    )

    foo_id: Mapped[int] = mapped_column(
        Integer, Identity(always=True, start=1, increment=1), primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(True), server_default=text("CURRENT_TIMESTAMP"), default=text("CURRENT_TIMESTAMP")
    )

    bars: Mapped[list["Bar"]] = relationship("Bar", cascade="save-update", back_populates="foo", init=False)
