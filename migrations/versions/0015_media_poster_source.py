"""记录媒体海报的独立来源

Revision ID: 0015_media_poster_source
Revises: 0014_media_discovery_core
Create Date: 2026-09-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0015_media_poster_source"
down_revision: Union[str, None] = "0014_media_discovery_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_subjects",
        sa.Column("last_known_poster_source", sa.Text(), nullable=True),
    )
    op.execute(
        """
        UPDATE media_subjects
        SET last_known_poster_source = snapshot_source
        WHERE last_known_poster_url IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("media_subjects", "last_known_poster_source")
