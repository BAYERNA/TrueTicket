"""Create verification schema and concurrency constraint.

Revision ID: verify_0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "verify_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("verification_logs"):
        op.create_table(
            "verification_logs",
            sa.Column("verification_id", sa.String(length=36), nullable=False),
            sa.Column("reservation_id", sa.String(length=36), nullable=False),
            sa.Column("qr_scanned_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("face_match_result", sa.Boolean(), nullable=False),
            sa.Column("face_match_score", sa.Float(), nullable=False),
            sa.Column("snapshot_uri", sa.String(length=500), nullable=False),
            sa.Column("duplicate_scan_flag", sa.Boolean(), nullable=False),
            sa.Column("verified_by", sa.String(length=100), nullable=False),
            sa.PrimaryKeyConstraint("verification_id"),
        )

    index_names = _index_names("verification_logs")
    if "ix_verification_logs_reservation_id" not in index_names:
        op.create_index(
            "ix_verification_logs_reservation_id",
            "verification_logs",
            ["reservation_id"],
        )
    if "idx_verification_logs_one_success_per_reservation" not in index_names:
        op.create_index(
            "idx_verification_logs_one_success_per_reservation",
            "verification_logs",
            ["reservation_id"],
            unique=True,
            postgresql_where=sa.text("face_match_result = true"),
        )


def downgrade() -> None:
    op.drop_table("verification_logs")
