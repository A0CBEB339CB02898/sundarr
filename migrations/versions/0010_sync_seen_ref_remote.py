"""更新 sync_seen_files 外键指向 remote_media_libraries

Revision ID: 0010_sync_seen_ref_remote
Revises: 0009_remote_media_lib_sync
Create Date: 2026-05-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_sync_seen_ref_remote"
down_revision: Union[str, None] = "0009_remote_media_lib_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("sync_seen_files_binding_id_fkey", "sync_seen_files", type_="foreignkey")
    op.create_foreign_key("sync_seen_files_binding_id_fkey", "sync_seen_files", "remote_media_libraries", ["binding_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("sync_seen_files_binding_id_fkey", "sync_seen_files", type_="foreignkey")
    op.create_foreign_key("sync_seen_files_binding_id_fkey", "sync_seen_files", "sync_bindings", ["binding_id"], ["id"])
