"""创建媒体发现 Core 数据表

Revision ID: 0014_media_discovery_core
Revises: 0013_plugin_config_diagnostics
Create Date: 2026-08-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0014_media_discovery_core"
down_revision: Union[str, None] = "0013_plugin_config_diagnostics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_subjects",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=False),
        sa.Column("canonical_title", sa.Text(), nullable=False),
        sa.Column("release_year", sa.Integer(), nullable=True),
        sa.Column("last_known_poster_url", sa.Text(), nullable=True),
        sa.Column("snapshot_source", sa.Text(), nullable=False),
        sa.Column("snapshot_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("followed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("watchlisted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_subjects_media_type", "media_subjects", ["media_type"])
    op.create_index("ix_media_subjects_canonical_title", "media_subjects", ["canonical_title"])
    op.create_index("ix_media_subjects_release_year", "media_subjects", ["release_year"])
    op.create_index("ix_media_subjects_followed_at", "media_subjects", ["followed_at"])
    op.create_index("ix_media_subjects_watchlisted_at", "media_subjects", ["watchlisted_at"])

    op.create_table(
        "media_external_ids",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("media_subject_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["media_subject_id"], ["media_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_id", name="uq_media_external_provider_id"),
    )
    op.create_index("ix_media_external_ids_media_subject_id", "media_external_ids", ["media_subject_id"])
    op.create_index("ix_media_external_ids_provider", "media_external_ids", ["provider"])

    op.create_table(
        "watchlist_sync_states",
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("provider_id"),
    )

    op.create_table(
        "media_watchlist_entries",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("external_record_id", sa.Text(), nullable=False),
        sa.Column("media_subject_id", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["media_subject_id"], ["media_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "external_record_id", name="uq_watchlist_provider_record"),
    )
    op.create_index("ix_media_watchlist_entries_provider_id", "media_watchlist_entries", ["provider_id"])
    op.create_index("ix_media_watchlist_entries_media_subject_id", "media_watchlist_entries", ["media_subject_id"])


def downgrade() -> None:
    op.drop_index("ix_media_watchlist_entries_media_subject_id", table_name="media_watchlist_entries")
    op.drop_index("ix_media_watchlist_entries_provider_id", table_name="media_watchlist_entries")
    op.drop_table("media_watchlist_entries")
    op.drop_table("watchlist_sync_states")
    op.drop_index("ix_media_external_ids_provider", table_name="media_external_ids")
    op.drop_index("ix_media_external_ids_media_subject_id", table_name="media_external_ids")
    op.drop_table("media_external_ids")
    op.drop_index("ix_media_subjects_watchlisted_at", table_name="media_subjects")
    op.drop_index("ix_media_subjects_followed_at", table_name="media_subjects")
    op.drop_index("ix_media_subjects_release_year", table_name="media_subjects")
    op.drop_index("ix_media_subjects_canonical_title", table_name="media_subjects")
    op.drop_index("ix_media_subjects_media_type", table_name="media_subjects")
    op.drop_table("media_subjects")
