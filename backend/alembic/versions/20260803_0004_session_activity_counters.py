"""Track durable session activity for analytics.

Revision ID: 20260803_0004
Revises: e100ba107f49
Create Date: 2026-08-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260803_0004"
down_revision: str | None = "e100ba107f49"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interaction_sessions",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "interaction_sessions",
        sa.Column(
            "message_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE interaction_sessions AS session
        SET message_count = activity.message_count,
            last_activity_at = activity.last_activity_at
        FROM (
            SELECT session_id,
                   COUNT(*)::integer AS message_count,
                   MAX(timestamp) AS last_activity_at
            FROM conversation_messages
            GROUP BY session_id
        ) AS activity
        WHERE activity.session_id = session.id
        """
    )
def downgrade() -> None:
    op.drop_column("interaction_sessions", "message_count")
    op.drop_column("interaction_sessions", "last_activity_at")
