"""为 SMB 和媒体库增加测试状态字段

Revision ID: 0011_test_status_columns
Revises: 0010_sync_seen_ref_remote
Create Date: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_test_status_columns"
down_revision: Union[str, None] = "0010_sync_seen_ref_remote"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table_name in ("smb_connections", "media_libraries", "remote_media_libraries"):
        op.add_column(table_name, sa.Column("last_test_ok", sa.Boolean(), nullable=True))
        op.add_column(table_name, sa.Column("last_test_error_code", sa.Text(), nullable=True))
        op.add_column(table_name, sa.Column("last_test_error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    for table_name in ("remote_media_libraries", "media_libraries", "smb_connections"):
        op.drop_column(table_name, "last_test_error_message")
        op.drop_column(table_name, "last_test_error_code")
        op.drop_column(table_name, "last_test_ok")
