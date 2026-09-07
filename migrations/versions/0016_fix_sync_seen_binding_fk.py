"""修正已发现文件对同步绑定的外键语义

Revision ID: 0016_fix_sync_seen_binding_fk
Revises: 0015_media_poster_source
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_fix_sync_seen_binding_fk"
down_revision: Union[str, None] = "0015_media_poster_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("sync_seen_files_binding_id_fkey", "sync_seen_files", type_="foreignkey")

    connection = op.get_bind()
    seen_rows = list(connection.execute(
        sa.text("SELECT id, binding_id FROM sync_seen_files WHERE binding_id IS NOT NULL")
    ).mappings())
    binding_rows = list(connection.execute(
        sa.text("SELECT id, remote_library_id FROM sync_bindings")
    ).mappings())
    bindings = binding_rows
    binding_ids = {str(row["id"]) for row in bindings}
    by_remote: dict[str, list[str]] = {}
    for row in bindings:
        by_remote.setdefault(str(row["remote_library_id"]), []).append(str(row["id"]))

    for row in seen_rows:
        current_id = str(row["binding_id"])
        if current_id in binding_ids:
            continue
        candidates = by_remote.get(current_id, [])
        if len(candidates) == 1:
            connection.execute(
                sa.text("UPDATE sync_seen_files SET binding_id = :binding_id WHERE id = :seen_id"),
                {"binding_id": candidates[0], "seen_id": row["id"]},
            )
        else:
            # 无法无损判断所属绑定时保留发现记录，但解除错误外键并等待重新扫描。
            connection.execute(
                sa.text(
                    "UPDATE sync_seen_files "
                    "SET binding_id = NULL, status = 'failed', task_id = NULL "
                    "WHERE id = :seen_id"
                ),
                {"seen_id": row["id"]},
            )

    op.create_foreign_key(
        "sync_seen_files_binding_id_fkey",
        "sync_seen_files",
        "sync_bindings",
        ["binding_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("sync_seen_files_binding_id_fkey", "sync_seen_files", type_="foreignkey")
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE sync_seen_files AS seen "
            "SET binding_id = binding.remote_library_id "
            "FROM sync_bindings AS binding "
            "WHERE seen.binding_id = binding.id"
        )
    )
    op.create_foreign_key(
        "sync_seen_files_binding_id_fkey",
        "sync_seen_files",
        "remote_media_libraries",
        ["binding_id"],
        ["id"],
    )
