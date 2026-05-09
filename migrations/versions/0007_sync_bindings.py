"""重构同步绑定表

Revision ID: 0007_sync_bindings
Revises: 0006_remote_media_libraries
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_sync_bindings"
down_revision: Union[str, None] = "0006_remote_media_libraries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_bindings",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=False),
        sa.Column("remote_library_id", sa.Text(), sa.ForeignKey("remote_media_libraries.id"), nullable=False),
        sa.Column("local_library_id", sa.Text(), sa.ForeignKey("media_libraries.id"), nullable=False),
        sa.Column("delete_source_after_success", sa.Boolean()),
        sa.Column("delete_empty_source_dirs", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "sync_seen_files",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("binding_id", sa.Text(), sa.ForeignKey("sync_bindings.id")),
        sa.Column("source_fingerprint", sa.Text(), nullable=False, unique=True),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_size", sa.BigInteger()),
        sa.Column("source_mtime", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Text(), sa.ForeignKey("transfer_tasks.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sync_seen_files_binding_id", "sync_seen_files", ["binding_id"])
    op.create_index("ix_sync_seen_files_status", "sync_seen_files", ["status"])


def downgrade() -> None:
    op.drop_index("ix_sync_seen_files_status", table_name="sync_seen_files")
    op.drop_index("ix_sync_seen_files_binding_id", table_name="sync_seen_files")
    op.drop_table("sync_seen_files")
    op.drop_table("sync_bindings")
