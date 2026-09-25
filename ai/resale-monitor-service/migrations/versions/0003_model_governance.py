"""Add scoring model version.

Revision ID: resale_0003
Revises: resale_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "resale_0003"
down_revision = "resale_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resale_listings", sa.Column("model_version", sa.String(100), nullable=False, server_default="resale-rules-v1"))


def downgrade() -> None:
    op.drop_column("resale_listings", "model_version")
