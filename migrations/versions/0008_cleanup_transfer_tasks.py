"""清理 TransferTask 字段

Revision ID: 0008_cleanup_transfer_tasks
Revises: 0007_sync_bindings
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_cleanup_transfer_tasks"
down_revision: Union[str, None] = "0007_sync_bindings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transfer_tasks", sa.Column("binding_id", sa.Text(), nullable=True))
    op.add_column("transfer_tasks", sa.Column("sync_seen_file_id", sa.Text(), nullable=True))
    op.execute("UPDATE transfer_tasks SET sync_seen_file_id = ingest_seen_file_id WHERE ingest_seen_file_id IS NOT NULL")
    op.drop_column("transfer_tasks", "ingest_seen_file_id")


def downgrade() -> None:
    op.add_column("transfer_tasks", sa.Column("ingest_seen_file_id", sa.Text(), nullable=True))
    op.execute("UPDATE transfer_tasks SET ingest_seen_file_id = sync_seen_file_id WHERE sync_seen_file_id IS NOT NULL")
    op.drop_column("transfer_tasks", "sync_seen_file_id")
    op.drop_column("transfer_tasks", "binding_id")
