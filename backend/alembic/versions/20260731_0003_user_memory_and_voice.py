"""Add per-user memory facts and voice gender preference.

Revision ID: 20260731_0003
Revises: 65edcce9b9c0
Create Date: 2026-07-31 18:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260731_0003"
down_revision: str | None = "65edcce9b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


voice_gender = postgresql.ENUM("male", "female", name="voice_gender")


def upgrade() -> None:
    bind = op.get_bind()
    voice_gender.create(bind, checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "preferred_voice_gender",
            postgresql.ENUM(
                "male",
                "female",
                name="voice_gender",
                create_type=False,
            ),
            server_default="male",
            nullable=False,
        ),
    )

    op.create_table(
        "user_memory_facts",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("fact_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_referenced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_memory_facts_user_id"),
        "user_memory_facts",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_memory_facts_user_id"),
        table_name="user_memory_facts",
    )
    op.drop_table("user_memory_facts")
    op.drop_column("users", "preferred_voice_gender")
    voice_gender.drop(op.get_bind(), checkfirst=True)
