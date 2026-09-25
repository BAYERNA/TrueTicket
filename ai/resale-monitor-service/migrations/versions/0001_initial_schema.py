"""Create resale monitoring schema and query indexes.

Revision ID: resale_0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "resale_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("sellers"):
        op.create_table(
            "sellers",
            sa.Column("seller_id", sa.String(length=36), nullable=False),
            sa.Column("platform_name", sa.String(length=50), nullable=False),
            sa.Column("external_seller_id", sa.String(length=100), nullable=False),
            sa.Column("listing_count", sa.Integer(), nullable=False),
            sa.Column("habitual_score", sa.Float(), nullable=False),
            sa.PrimaryKeyConstraint("seller_id"),
        )
    seller_indexes = _index_names("sellers")
    if "ix_sellers_external_seller_id" not in seller_indexes:
        op.create_index("ix_sellers_external_seller_id", "sellers", ["external_seller_id"])
    if "idx_sellers_habitual_score" not in seller_indexes:
        op.create_index("idx_sellers_habitual_score", "sellers", ["habitual_score"])

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("resale_listings"):
        op.create_table(
            "resale_listings",
            sa.Column("listing_id", sa.String(length=36), nullable=False),
            sa.Column("seller_id", sa.String(length=36), nullable=False),
            sa.Column("platform_name", sa.String(length=50), nullable=False),
            sa.Column("event_title_matched", sa.String(length=255), nullable=False),
            sa.Column("listed_price", sa.Float(), nullable=False),
            sa.Column("price_anomaly_score", sa.Float(), nullable=False),
            sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["seller_id"], ["sellers.seller_id"]),
            sa.PrimaryKeyConstraint("listing_id"),
        )
    listing_indexes = _index_names("resale_listings")
    if "ix_resale_listings_seller_id" not in listing_indexes:
        op.create_index("ix_resale_listings_seller_id", "resale_listings", ["seller_id"])
    if "idx_resale_listings_event_price" not in listing_indexes:
        op.create_index(
            "idx_resale_listings_event_price",
            "resale_listings",
            ["event_title_matched", "listed_price"],
        )


def downgrade() -> None:
    op.drop_table("resale_listings")
    op.drop_table("sellers")
