from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sundarr"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://sundarr:sundarr@localhost:5432/sundarr"
    redis_url: str = "redis://localhost:6379/0"
    cloud_staging_root: str = "/Sundarr/_staging"

    model_config = SettingsConfigDict(
        env_file=".env",
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
