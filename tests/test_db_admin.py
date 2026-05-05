from sundarr.app.db_admin import _build_maintenance_url


def test_build_maintenance_url_uses_postgres_database() -> None:
    url = _build_maintenance_url("postgresql+psycopg://user:secret@db.example:5432/sundarr")

    assert url == "postgresql://user:secret@db.example:5432/postgres"
