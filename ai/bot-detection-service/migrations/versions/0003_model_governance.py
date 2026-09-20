"""Add model version and human review labels.

Revision ID: bot_0003
Revises: bot_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "bot_0003"
down_revision = "bot_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bot_scores", sa.Column("model_version", sa.String(100), nullable=False, server_default="bot-rules-v1"))
    op.add_column("bot_scores", sa.Column("review_label", sa.String(30), nullable=True))
    op.add_column("bot_scores", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("bot_scores", "reviewed_at")
    op.drop_column("bot_scores", "review_label")
    op.drop_column("bot_scores", "model_version")
