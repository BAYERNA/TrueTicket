"""Create bot detection schema and indexes.

Revision ID: bot_0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bot_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("behavior_logs"):
        op.create_table(
            "behavior_logs",
            sa.Column("log_id", sa.String(length=36), nullable=False),
            sa.Column("reservation_session_id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("log_id"),
        )
    if "ix_behavior_logs_reservation_session_id" not in _index_names("behavior_logs"):
        op.create_index(
            "ix_behavior_logs_reservation_session_id",
            "behavior_logs",
            ["reservation_session_id"],
        )

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("bot_scores"):
        op.create_table(
            "bot_scores",
            sa.Column("score_id", sa.String(length=36), nullable=False),
            sa.Column("reservation_session_id", sa.String(length=36), nullable=False),
            sa.Column("acquisition_fraud_score", sa.Float(), nullable=False),
            sa.Column("is_flagged", sa.Boolean(), nullable=False),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("score_id"),
        )
    if "ix_bot_scores_reservation_session_id" not in _index_names("bot_scores"):
        op.create_index(
            "ix_bot_scores_reservation_session_id",
            "bot_scores",
            ["reservation_session_id"],
        )


def downgrade() -> None:
    op.drop_table("bot_scores")
    op.drop_table("behavior_logs")
