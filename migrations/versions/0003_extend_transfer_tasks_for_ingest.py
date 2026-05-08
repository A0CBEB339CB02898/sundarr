"""扩展任务表支持挂载网盘导入来源

Revision ID: 0003_ingest_task_source
Revises: 0002_create_ingest_tables
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_ingest_task_source"
down_revision: Union[str, None] = "0002_create_ingest_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("transfer_tasks", "link_id", nullable=True)
    op.add_column("transfer_tasks", sa.Column("source_type", sa.Text()))
    op.add_column("transfer_tasks", sa.Column("source_path", sa.Text()))
    op.add_column("transfer_tasks", sa.Column("source_config_snapshot", postgresql.JSONB()))
    op.add_column("transfer_tasks", sa.Column("ingest_seen_file_id", sa.Text()))
    op.create_index("ix_transfer_tasks_ingest_seen_file_id", "transfer_tasks", ["ingest_seen_file_id"])


def downgrade() -> None:
    op.drop_index("ix_transfer_tasks_ingest_seen_file_id", table_name="transfer_tasks")
    op.drop_column("transfer_tasks", "ingest_seen_file_id")
    op.drop_column("transfer_tasks", "source_config_snapshot")
    op.drop_column("transfer_tasks", "source_path")
    op.drop_column("transfer_tasks", "source_type")
    op.alter_column("transfer_tasks", "link_id", nullable=False)
