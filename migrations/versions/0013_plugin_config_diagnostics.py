"""增加插件实例独立错误状态

Revision ID: 0013_plugin_config_diagnostics
Revises: 0008
Create Date: 2026-08-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0013_plugin_config_diagnostics"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plugin_configs", sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("plugin_configs", "last_error")
