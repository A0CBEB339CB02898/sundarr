"""创建 SMB 连接和媒体库表

Revision ID: 0004_smb_connections_media_libs
Revises: 0003_ingest_task_source
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_smb_connections_media_libs"
down_revision: Union[str, None] = "0003_ingest_task_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "smb_connections",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("port", sa.Integer(), server_default="445", nullable=False),
        sa.Column("share", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password", sa.Text()),
        sa.Column("domain", sa.Text()),
        sa.Column("base_path", sa.Text(), server_default="/", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "media_libraries",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("connection_id", sa.Text(), sa.ForeignKey("smb_connections.id"), nullable=False),
        sa.Column("base_path", sa.Text(), server_default="/", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("media_libraries")
    op.drop_table("smb_connections")
