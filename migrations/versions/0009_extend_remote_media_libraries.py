"""扩展远程媒体库支持同步配置和绑定

Revision ID: 0009_extend_remote_media_libraries
Revises: 0008_cleanup_transfer_tasks
Create Date: 2026-05-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_extend_remote_media_libraries"
down_revision: Union[str, None] = "0008_cleanup_transfer_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("remote_media_libraries", sa.Column("target_library_id", sa.Text(), sa.ForeignKey("media_libraries.id"), nullable=True))
    op.add_column("remote_media_libraries", sa.Column("scan_interval_seconds", sa.Integer(), server_default="60", nullable=False))
    op.add_column("remote_media_libraries", sa.Column("stable_seconds", sa.Integer(), server_default="120", nullable=False))
    op.add_column("remote_media_libraries", sa.Column("delete_source_after_success", sa.Boolean(), nullable=True))
    op.add_column("remote_media_libraries", sa.Column("delete_empty_source_dirs", sa.Boolean(), nullable=True))

    op.execute("""
        UPDATE remote_media_libraries
        SET target_library_id = sb.local_library_id
        FROM sync_bindings sb
        WHERE sb.remote_library_id = remote_media_libraries.id
        AND sb.local_library_id IS NOT NULL
    """)

    op.execute("""
        UPDATE remote_media_libraries
        SET scan_interval_seconds = COALESCE(
            (SELECT (value_json->>'scan_interval_seconds')::int FROM settings WHERE key = 'download_to_local.config'),
            60
        ),
        stable_seconds = COALESCE(
            (SELECT (value_json->>'stable_seconds')::int FROM settings WHERE key = 'download_to_local.config'),
            120
        )
    """)


def downgrade() -> None:
    op.drop_column("remote_media_libraries", "delete_empty_source_dirs")
    op.drop_column("remote_media_libraries", "delete_source_after_success")
    op.drop_column("remote_media_libraries", "stable_seconds")
    op.drop_column("remote_media_libraries", "scan_interval_seconds")
    op.drop_column("remote_media_libraries", "target_library_id")
