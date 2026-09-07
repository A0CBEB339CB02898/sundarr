"""显式 PostgreSQL 迁移验收；默认离线测试跳过。"""

from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from sundarr.app.config import PROJECT_ROOT, get_settings
from sundarr.app.models import Resource, ResourceLink, TransferTask
from sundarr.app.worker import WorkerSettings, claim_pending_tasks


@pytest.mark.postgres_integration
def test_fresh_postgres_reaches_clean_head(monkeypatch: pytest.MonkeyPatch) -> None:
    base_url_value = os.environ.get("SUNDARR_TEST_POSTGRES_URL", "").strip()
    if not base_url_value:
        pytest.skip("未配置 SUNDARR_TEST_POSTGRES_URL")

    base_url = make_url(base_url_value)
    database_name = f"sundarr_migration_test_{uuid4().hex[:12]}"
    maintenance_url = base_url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    test_url = base_url.set(database=database_name).render_as_string(hide_password=False)

    with psycopg.connect(maintenance_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))

    try:
        monkeypatch.setenv("SUNDARR_DATABASE_URL", test_url)
        get_settings.cache_clear()
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
        config.set_main_option("prepend_sys_path", str(PROJECT_ROOT))
        command.upgrade(config, "head")
        command.check(config)

        engine = create_engine(test_url)
        try:
            foreign_keys = inspect(engine).get_foreign_keys("sync_seen_files")
            _assert_skip_locked_claims_next_task(engine)
        finally:
            engine.dispose()
        binding_fk = next(item for item in foreign_keys if item["constrained_columns"] == ["binding_id"])
        assert binding_fk["referred_table"] == "sync_bindings"
    finally:
        get_settings.cache_clear()
        with psycopg.connect(maintenance_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_name)))


def _assert_skip_locked_claims_next_task(engine) -> None:
    """两个数据库事务不能认领同一个 pending 任务。"""

    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as seed:
        resource = Resource(id="pg_resource", title="PostgreSQL 认领测试", normalized_title="postgres claim")
        link = ResourceLink(id="pg_link", resource_id=resource.id, provider="local", url="local://claim")
        seed.add_all(
            [
                resource,
                link,
                TransferTask(
                    id="pg_task_1",
                    resource_id=resource.id,
                    link_id=link.id,
                    status="pending",
                    mode="copy",
                    target_type="local",
                    target_path="Movies/One.mkv",
                ),
                TransferTask(
                    id="pg_task_2",
                    resource_id=resource.id,
                    link_id=link.id,
                    status="pending",
                    mode="copy",
                    target_type="local",
                    target_path="Movies/Two.mkv",
                ),
            ]
        )
        seed.commit()

    first = session_factory()
    second = session_factory()
    try:
        first.query(TransferTask).filter(TransferTask.id == "pg_task_1").with_for_update().one()

        claimed = claim_pending_tasks(second, WorkerSettings(enabled=True, concurrency=1))

        assert [task.id for task in claimed] == ["pg_task_2"]
        assert second.get(TransferTask, "pg_task_1").status == "pending"
        assert second.get(TransferTask, "pg_task_2").status == "staging_to_cloud"
    finally:
        first.rollback()
        first.close()
        second.close()
