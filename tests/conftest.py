import hashlib
import re
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from sundarr.app import models  # noqa: F401
from sundarr.app.core.database import Base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTEST_TMP_ROOT = PROJECT_ROOT / ".sundarr" / "pytest-tmp"


@pytest.fixture()
def tmp_path(request: pytest.FixtureRequest) -> Generator[Path, None, None]:
    """使用项目内临时目录，避免 Windows 下 pytest 内置 basetemp 生成私有 ACL。"""
    PYTEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    node_id = request.node.nodeid
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", node_id)[-80:]
    digest = hashlib.sha1(node_id.encode("utf-8")).hexdigest()[:8]
    path = PYTEST_TMP_ROOT / f"{safe_name}-{digest}"
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
