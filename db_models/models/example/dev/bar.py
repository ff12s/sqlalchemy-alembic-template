# OVERRIDE: dev-тир добавляет к example.bar диагностическую колонку debug_note.
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Identity, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.models.example import BaseExample

if TYPE_CHECKING:
    from db_models.models.example.foo import Foo


class Bar(BaseExample):
    """Пример дочерней модели с tier-специфичной колонкой (dev-override).

    Поля:
        - **`bar_id`**: Integer, not nullable, pkey
        - **`foo_id`**: Integer, nullable, fkey -> example.foo.foo_id
        - **`value`**: String(255), nullable
        - **`debug_note`**: String(500), nullable

    Отношения:
        - **`foo`**: db_models.models.example.foo.Foo
    """

    __tablename__ = "bar"
    __table_args__ = BaseExample.with_constraints(
        PrimaryKeyConstraint("bar_id", name="bar_pkey"),
    )

    bar_id: Mapped[int] = mapped_column(
        Integer, Identity(always=True, start=1, increment=1), primary_key=True, init=False
    )
    foo_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("example.foo.foo_id", ondelete="CASCADE", onupdate="CASCADE", name="bar_foo_id_fkey"),
        default=None,
    )
    value: Mapped[str | None] = mapped_column(String(255), default=None)
    debug_note: Mapped[str | None] = mapped_column(String(500), default=None)

    foo: Mapped["Foo | None"] = relationship("Foo", back_populates="bars", init=False)
