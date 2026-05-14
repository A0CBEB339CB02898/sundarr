"""重构搜索源目录表

Revision ID: 0012_refactor_sources_catalog
Revises: 0011_test_status_columns
Create Date: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_refactor_sources_catalog"
down_revision: Union[str, None] = "0011_test_status_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("description", sa.Text(), server_default="", nullable=False))
    op.add_column("sources", sa.Column("homepage_url", sa.Text(), server_default="", nullable=False))
    op.add_column("sources", sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for column_name in (
        "type",
        "enabled",
        "legal_note",
        "trust_level",
        "created_by_user",
        "config_json",
        "last_error_code",
        "last_error_message",
        "last_checked_at",
    ):
        op.drop_column("sources", column_name)


def downgrade() -> None:
    op.add_column("sources", sa.Column("last_checked_at", sa.DateTime(timezone=True)))
    op.add_column("sources", sa.Column("last_error_message", sa.Text()))
    op.add_column("sources", sa.Column("last_error_code", sa.Text()))
    op.add_column("sources", sa.Column("config_json", sa.JSON()))
    op.add_column("sources", sa.Column("created_by_user", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("sources", sa.Column("trust_level", sa.Integer(), server_default="1", nullable=False))
    op.add_column("sources", sa.Column("legal_note", sa.Text()))
    op.add_column("sources", sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("sources", sa.Column("type", sa.Text(), server_default="code", nullable=False))
    op.drop_column("sources", "registered_at")
    op.drop_column("sources", "homepage_url")
    op.drop_column("sources", "description")
