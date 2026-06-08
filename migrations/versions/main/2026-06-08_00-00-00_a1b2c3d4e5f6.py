"""initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-06-08 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = ("main",)
depends_on = None


def upgrade():
    op.create_table(
        "foo",
        sa.Column("foo_id", sa.Integer(), sa.Identity(always=True, start=1, increment=1), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("foo_id", name="foo_pkey"),
        sa.UniqueConstraint("name", name="foo_name_uk"),
        schema="example",
    )
    op.create_table(
        "bar",
        sa.Column("bar_id", sa.Integer(), sa.Identity(always=True, start=1, increment=1), nullable=False),
        sa.Column("foo_id", sa.Integer(), nullable=True),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["foo_id"],
            ["example.foo.foo_id"],
            name="bar_foo_id_fkey",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("bar_id", name="bar_pkey"),
        schema="example",
    )


def downgrade():
    op.drop_table("bar", schema="example")
    op.drop_table("foo", schema="example")
