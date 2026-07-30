"""Create phase 1 face recognition models.

Revision ID: 20260730_0001
Revises:
Create Date: 2026-07-30 12:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260730_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_status = postgresql.ENUM("active", "inactive", name="user_status")
message_role = postgresql.ENUM("user", "assistant", name="message_role")
recognition_outcome = postgresql.ENUM(
    "recognized",
    "unrecognized",
    "spoof_detected",
    name="recognition_outcome",
)


def upgrade() -> None:
    bind = op.get_bind()
    user_status.create(bind, checkfirst=True)
    message_role.create(bind, checkfirst=True)
    recognition_outcome.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preferred_language", sa.String(length=10), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "inactive",
                name="user_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "face_embeddings",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "embedding_vector",
            postgresql.ARRAY(sa.Float()),
            nullable=False,
        ),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_image_path", sa.String(length=500), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_face_embeddings_user_id"),
        "face_embeddings",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "interaction_sessions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_emotion_summary", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interaction_sessions_user_id"),
        "interaction_sessions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "recognition_events",
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "outcome",
            postgresql.ENUM(
                "recognized",
                "unrecognized",
                "spoof_detected",
                name="recognition_outcome",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_recognition_events_user_id"),
        "recognition_events",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "conversation_messages",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "user",
                "assistant",
                name="message_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["interaction_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_messages_session_id"),
        "conversation_messages",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_conversation_messages_session_id"),
        table_name="conversation_messages",
    )
    op.drop_table("conversation_messages")
    op.drop_index(
        op.f("ix_recognition_events_user_id"),
        table_name="recognition_events",
    )
    op.drop_table("recognition_events")
    op.drop_index(
        op.f("ix_interaction_sessions_user_id"),
        table_name="interaction_sessions",
    )
    op.drop_table("interaction_sessions")
    op.drop_index(
        op.f("ix_face_embeddings_user_id"),
        table_name="face_embeddings",
    )
    op.drop_table("face_embeddings")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    recognition_outcome.drop(bind, checkfirst=True)
    message_role.drop(bind, checkfirst=True)
    user_status.drop(bind, checkfirst=True)

