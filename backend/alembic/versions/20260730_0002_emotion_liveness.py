"""Add emotion and liveness results to recognition events.

Revision ID: 20260730_0002
Revises: 20260730_0001
Create Date: 2026-07-30 13:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260730_0002"
down_revision: str | None = "20260730_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "recognition_events",
        sa.Column("detected_emotion", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "recognition_events",
        sa.Column("emotion_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "recognition_events",
        sa.Column("liveness_confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recognition_events", "liveness_confidence")
    op.drop_column("recognition_events", "emotion_confidence")
    op.drop_column("recognition_events", "detected_emotion")

