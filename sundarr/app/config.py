from functools import lru_cache

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
