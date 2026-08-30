from fastapi import FastAPI
from fastapi.testclient import TestClient

from sundarr.app.api import configuration as configuration_api
from sundarr.app.core.database import get_db
from sundarr.app.models import MediaLibrary, RemoteMediaLibrary, SmbConnection, SyncBinding


class FakePluginManager:
    def __init__(self, plugins=None):
        self.plugins = plugins or []

    def list_plugins(self, _session):
        return self.plugins


def make_client(db_session, monkeypatch, plugins=None) -> TestClient:
    monkeypatch.setattr(configuration_api, "plugin_manager", FakePluginManager(plugins))
    app = FastAPI()
    app.include_router(configuration_api.router)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_readiness_returns_catalog_and_first_sync_step_without_sensitive_values(db_session, monkeypatch) -> None:
    client = make_client(db_session, monkeypatch)

    response = client.get("/configuration/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert {item["id"] for item in body["issues"]} == {"catalog-provider-missing", "smb-connection-missing"}
    assert len(body["fingerprint"]) == 20
    assert "token" not in response.text.lower()


def test_readiness_reports_plugin_required_fields_without_values(db_session, monkeypatch) -> None:
    plugins = [{
        "id": "tmdb-catalog",
        "name": "TMDb 目录",
        "plugin_type": "catalog_provider",
        "enabled": False,
        "configuration_required": True,
        "missing_required_config": ["api_read_access_token"],
        "config_schema": {"api_read_access_token": {"label": "TMDb API Read Access Token"}},
    }]
    client = make_client(db_session, monkeypatch, plugins)

    body = client.get("/configuration/readiness").json()

    issue = next(item for item in body["issues"] if item["id"] == "plugin-required-config:tmdb-catalog")
    assert issue["action_path"] == "/app/plugins?plugin_id=tmdb-catalog"
    assert "TMDb API Read Access Token" in issue["message"]


def test_readiness_advances_sync_setup_and_changes_fingerprint(db_session, monkeypatch) -> None:
    configured_catalog = [{
        "id": "catalog",
        "name": "目录",
        "plugin_type": "catalog_provider",
        "enabled": True,
        "configuration_required": False,
        "missing_required_config": [],
    }]
    client = make_client(db_session, monkeypatch, configured_catalog)
    first = client.get("/configuration/readiness").json()

    db_session.add(SmbConnection(id="smb", name="NAS", host="nas", port=445, share="media", username="user", base_path="/"))
    db_session.commit()
    second = client.get("/configuration/readiness").json()

    assert [item["id"] for item in first["issues"]] == ["smb-connection-missing"]
    assert [item["id"] for item in second["issues"]] == ["local-library-missing"]
    assert first["fingerprint"] != second["fingerprint"]

    db_session.add(MediaLibrary(id="local", name="电影", media_type="movie", connection_id="smb", base_path="Movies"))
    db_session.add(RemoteMediaLibrary(id="remote", name="远程", media_type="movie", connection_id="smb", base_path="Incoming"))
    db_session.flush()
    db_session.add(SyncBinding(id="binding", name="同步", media_type="movie", remote_library_id="remote", local_library_id="local"))
    db_session.commit()

    final = client.get("/configuration/readiness").json()
    assert final == {"ready": True, "fingerprint": "ready", "issues": []}
