"""Add snapshot retention audit field.

Revision ID: verify_0002
Revises: verify_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "verify_0002"
down_revision = "verify_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("verification_logs", sa.Column("snapshot_deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_verification_snapshot_retention", "verification_logs", ["qr_scanned_at", "snapshot_deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_verification_snapshot_retention", table_name="verification_logs")
    op.drop_column("verification_logs", "snapshot_deleted_at")
