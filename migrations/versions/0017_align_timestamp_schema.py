"""统一插件与收藏时间字段的 PostgreSQL 时区语义

Revision ID: 0017_align_timestamp_schema
Revises: 0016_fix_sync_seen_binding_fk
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_align_timestamp_schema"
down_revision: Union[str, None] = "0016_fix_sync_seen_binding_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PLUGIN_TABLES = ("plugin_repositories", "plugin_configs", "plugin_logs")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    required_columns = {
        "resources": {
            "favorited_at": sa.Column("favorited_at", sa.DateTime(timezone=True), nullable=True),
        },
        "resource_links": {
            "name": sa.Column("name", sa.Text(), nullable=True),
            "quality": sa.Column("quality", sa.Text(), nullable=True),
            "favorited_at": sa.Column("favorited_at", sa.DateTime(timezone=True), nullable=True),
            "published_at": sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        },
    }
    added_columns: set[tuple[str, str]] = set()
    for table_name, columns in required_columns.items():
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column_name, column in columns.items():
            if column_name not in existing:
                op.add_column(table_name, column)
                added_columns.add((table_name, column_name))

    for table_name in PLUGIN_TABLES:
        for column_name in ("created_at", "updated_at"):
            op.execute(
                sa.text(
                    f'UPDATE "{table_name}" SET "{column_name}" = now() '
                    f'WHERE "{column_name}" IS NULL'
                )
            )
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.DateTime(),
                type_=sa.DateTime(timezone=True),
                existing_nullable=True,
                nullable=False,
                postgresql_using=f'"{column_name}" AT TIME ZONE \'UTC\'',
            )

    for table_name, column_name in (
        ("resources", "favorited_at"),
        ("resource_links", "favorited_at"),
        ("resource_links", "published_at"),
    ):
        if (table_name, column_name) in added_columns:
            continue
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True,
            postgresql_using=f'"{column_name}" AT TIME ZONE \'UTC\'',
        )


def downgrade() -> None:
    for table_name, column_name in (
        ("resources", "favorited_at"),
        ("resource_links", "favorited_at"),
        ("resource_links", "published_at"),
    ):
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=True,
            postgresql_using=f'"{column_name}" AT TIME ZONE \'UTC\'',
        )

    for table_name in PLUGIN_TABLES:
        for column_name in ("created_at", "updated_at"):
            op.alter_column(
                table_name,
                column_name,
                existing_type=sa.DateTime(timezone=True),
                type_=sa.DateTime(),
                existing_nullable=False,
                nullable=True,
                postgresql_using=f'"{column_name}" AT TIME ZONE \'UTC\'',
            )

    # 新增字段也可能来自旧版运行时自修复，降级不删除业务数据。
