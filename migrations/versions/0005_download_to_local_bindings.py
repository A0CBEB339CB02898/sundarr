"""创建下载到本地绑定和已见文件表

Revision ID: 0005_download_to_local_bindings
Revises: 0004_smb_connections_media_libs
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_download_to_local_bindings"
down_revision: Union[str, None] = "0004_smb_connections_media_libs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "download_to_local_bindings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=False),
        sa.Column("source_connection_id", sa.Text(), sa.ForeignKey("smb_connections.id"), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("target_library_id", sa.Text(), sa.ForeignKey("media_libraries.id"), nullable=False),
        sa.Column("delete_source_after_success", sa.Boolean()),
        sa.Column("delete_empty_source_dirs", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "download_to_local_seen_files",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("binding_id", sa.Text(), sa.ForeignKey("download_to_local_bindings.id")),
        sa.Column("source_fingerprint", sa.Text(), nullable=False, unique=True),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_size", sa.BigInteger()),
        sa.Column("source_mtime", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), sa.ForeignKey("transfer_tasks.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_dtl_seen_files_binding_id", "download_to_local_seen_files", ["binding_id"])
    op.create_index("ix_dtl_seen_files_status", "download_to_local_seen_files", ["status"])


def downgrade() -> None:
    op.drop_index("ix_dtl_seen_files_status", table_name="download_to_local_seen_files")
    op.drop_index("ix_dtl_seen_files_binding_id", table_name="download_to_local_seen_files")
    op.drop_table("download_to_local_seen_files")
    op.drop_table("download_to_local_bindings")
