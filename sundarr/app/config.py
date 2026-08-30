from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root(start: Path | None = None) -> Path:
    start_path = (start or Path.cwd()).resolve()
    candidates = [start_path, *start_path.parents]
    for candidate in candidates:
        if _is_project_root(candidate):
            return candidate

    package_path = Path(__file__).resolve()
    for candidate in package_path.parents:
        if _is_project_root(candidate):
            return candidate
    return Path.cwd().resolve()


def _is_project_root(path: Path) -> bool:
    return (
        (path / "pyproject.toml").exists()
        and (path / "alembic.ini").exists()
        and (path / "web" / "package.json").exists()
    )


PROJECT_ROOT = find_project_root()


class Settings(BaseSettings):
    app_name: str = "Sundarr"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://sundarr:sundarr@localhost:5432/sundarr"
    redis_url: str = "redis://localhost:6379/0"
    catalog_cache_ttl_seconds: int = 900
    catalog_detail_cache_ttl_seconds: int = 21600
    catalog_stale_ttl_seconds: int = 604800

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="SUNDARR_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def redact_url_password(url: str) -> str:
    parts = urlsplit(url)
    if not parts.password:
        return url
    username = parts.username or ""
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    auth = f"{username}:***@" if username else ":***@"
    return urlunsplit((parts.scheme, f"{auth}{host}{port}", parts.path, parts.query, parts.fragment))
