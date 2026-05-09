"""创建远程媒体库表

Revision ID: 0006_remote_media_libraries
Revises: 0005_download_to_local_bindings
Create Date: 2026-05-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_remote_media_libraries"
down_revision: Union[str, None] = "0005_download_to_local_bindings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "remote_media_libraries",
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
    op.drop_table("remote_media_libraries")
