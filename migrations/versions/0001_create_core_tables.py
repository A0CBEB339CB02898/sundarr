"""创建核心数据表

Revision ID: 0001_create_core_tables
Revises: 
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("legal_note", sa.Text()),
        sa.Column("trust_level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("config_json", postgresql.JSONB()),
        sa.Column("last_error_code", sa.Text()),
        sa.Column("last_error_message", sa.Text()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "resources",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text()),
        sa.Column("original_title", sa.Text()),
        sa.Column("type", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("season", sa.Integer()),
        sa.Column("episodes", sa.Text()),
        sa.Column("quality", sa.Text()),
        sa.Column("language", sa.Text()),
        sa.Column("subtitle", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("poster", sa.Text()),
        sa.Column("score", sa.Float(), server_default="0", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value_json", postgresql.JSONB(), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "resource_links",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("resource_id", sa.Text(), sa.ForeignKey("resources.id"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("code", sa.Text()),
        sa.Column("source_id", sa.Text(), sa.ForeignKey("sources.id")),
        sa.Column("source_url", sa.Text()),
        sa.Column("valid", sa.Boolean()),
        sa.Column("risk_level", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("visibility", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resource_links_resource_id", "resource_links", ["resource_id"])
    op.create_index("ix_resource_links_provider", "resource_links", ["provider"])

    op.create_table(
        "transfer_tasks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("resource_id", sa.Text(), sa.ForeignKey("resources.id")),
        sa.Column("link_id", sa.Text(), sa.ForeignKey("resource_links.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("cloud_staging_path", sa.Text()),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_library", sa.Text()),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("storage_config_snapshot", postgresql.JSONB()),
        sa.Column("total_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("done_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("speed_bytes_per_sec", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("retryable", sa.Boolean()),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_transfer_tasks_status", "transfer_tasks", ["status"])

    op.create_table(
        "transfer_files",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("task_id", sa.Text(), sa.ForeignKey("transfer_tasks.id"), nullable=False),
        sa.Column("cloud_file_id", sa.Text()),
        sa.Column("cloud_path", sa.Text(), nullable=False),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("temp_path", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("done_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transfer_files_task_id", "transfer_files", ["task_id"])
    op.create_index("ix_transfer_files_status", "transfer_files", ["status"])

    op.create_table(
        "transfer_logs",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("task_id", sa.Text(), sa.ForeignKey("transfer_tasks.id"), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("data_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transfer_logs_task_id", "transfer_logs", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_transfer_logs_task_id", table_name="transfer_logs")
    op.drop_table("transfer_logs")
    op.drop_index("ix_transfer_files_status", table_name="transfer_files")
    op.drop_index("ix_transfer_files_task_id", table_name="transfer_files")
    op.drop_table("transfer_files")
    op.drop_index("ix_transfer_tasks_status", table_name="transfer_tasks")
    op.drop_table("transfer_tasks")
    op.drop_index("ix_resource_links_provider", table_name="resource_links")
    op.drop_index("ix_resource_links_resource_id", table_name="resource_links")
    op.drop_table("resource_links")
    op.drop_table("settings")
    op.drop_table("resources")
    op.drop_table("sources")
