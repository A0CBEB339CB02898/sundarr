"""创建挂载网盘导入数据表

Revision ID: 0002_create_ingest_tables
Revises: 0001_create_core_tables
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_ingest_tables"
down_revision: Union[str, None] = "0001_create_core_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingest_bindings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=False),
        sa.Column("source_smb_json", postgresql.JSONB(), nullable=False),
        sa.Column("target_smb_json", postgresql.JSONB(), nullable=False),
        sa.Column("delete_source_after_success", sa.Boolean()),
        sa.Column("delete_empty_source_dirs", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingest_bindings_enabled", "ingest_bindings", ["enabled"])
    op.create_index("ix_ingest_bindings_media_type", "ingest_bindings", ["media_type"])

    op.create_table(
        "ingest_seen_files",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("binding_id", sa.Text(), sa.ForeignKey("ingest_bindings.id")),
        sa.Column("source_fingerprint", sa.Text(), nullable=False, unique=True),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_size", sa.BigInteger()),
        sa.Column("source_mtime", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), sa.ForeignKey("transfer_tasks.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingest_seen_files_binding_id", "ingest_seen_files", ["binding_id"])
    op.create_index("ix_ingest_seen_files_status", "ingest_seen_files", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingest_seen_files_status", table_name="ingest_seen_files")
    op.drop_index("ix_ingest_seen_files_binding_id", table_name="ingest_seen_files")
    op.drop_table("ingest_seen_files")
    op.drop_index("ix_ingest_bindings_media_type", table_name="ingest_bindings")
    op.drop_index("ix_ingest_bindings_enabled", table_name="ingest_bindings")
    op.drop_table("ingest_bindings")
