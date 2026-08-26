"""create plugin tables

Revision ID: 0008
Revises: 0012_refactor_sources_catalog
Create Date: 2026-06-25 12:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0012_refactor_sources_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create plugin tables."""

    # Create plugin_repositories table
    op.create_table(
        "plugin_repositories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("repo_url", sa.String(), nullable=False),
        sa.Column("branch", sa.String(), server_default="main", nullable=True),
        sa.Column("current_commit", sa.String(), nullable=True),
        sa.Column("previous_commit", sa.String(), nullable=True),
        sa.Column("auto_update", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=True),
        sa.Column("status", sa.String(), server_default="pending", nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_loaded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plugin_repositories_repo_url",
        "plugin_repositories",
        ["repo_url"],
        unique=True,
    )

    # Create plugin_configs table
    op.create_table(
        "plugin_configs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plugin_id", sa.String(), nullable=False),
        sa.Column("plugin_type", sa.String(), nullable=False),
        sa.Column("config_data", sa.Text(), server_default="{}", nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=True),
        sa.Column("status", sa.String(), server_default="active", nullable=True),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["plugin_repositories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plugin_configs_plugin_id",
        "plugin_configs",
        ["plugin_id"],
        unique=True,
    )

    # Create plugin_logs table
    op.create_table(
        "plugin_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("plugin_id", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plugin_logs_plugin_id",
        "plugin_logs",
        ["plugin_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop plugin tables."""

    op.drop_table("plugin_logs")
    op.drop_table("plugin_configs")
    op.drop_table("plugin_repositories")
