from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.main import create_app
from sundarr.app.models import IngestBinding, IngestSeenFile, Setting, TransferFile, TransferTask
from sundarr.app.services.ingest_service import INGEST_CONFIG_KEY, ingest_service


def make_client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def binding_payload(binding_id: str = "movie_binding") -> dict:
    return {
        "id": binding_id,
        "name": "电影导入",
        "enabled": True,
        "media_type": "movie",
        "source_smb": {
            "host": "nas.example.invalid",
            "port": 445,
            "share": "cloud",
            "username": "user",
            "password": "source-secret",
            "domain": "",
            "base_path": "/cloud/movie",
        },
        "target_smb": {
            "host": "nas.example.invalid",
            "port": 445,
            "share": "media",
            "username": "user",
            "password": "target-secret",
            "domain": "",
            "base_path": "/movie",
        },
        "delete_source_after_success": None,
        "delete_empty_source_dirs": None,
    }


def test_get_and_save_ingest_config(db_session: Session) -> None:
    client = make_client(db_session)

    get_response = client.get("/ingest/config")

    assert get_response.status_code == 200
    assert get_response.json()["delete_source_after_success"] is True
    assert get_response.json()["unclassified_target_path"] == "/unclassified"

    save_response = client.post(
        "/ingest/config/save",
        json={
            "delete_source_after_success": False,
            "delete_empty_source_dirs": False,
            "scan_interval_seconds": 30,
            "stable_seconds": 60,
            "unclassified_target_path": "/unclassified_media",
        },
    )

    assert save_response.status_code == 200
    assert save_response.json()["delete_source_after_success"] is False
    setting = db_session.get(Setting, INGEST_CONFIG_KEY)
    assert setting is not None
    assert setting.value_json["unclassified_target_path"] == "/unclassified_media"


def test_create_and_list_ingest_binding_redacts_password(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.post("/ingest/bindings/create", json=binding_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "movie_binding"
    assert body["source_smb"]["password_set"] is True
    assert "password" not in body["source_smb"]
    assert body["target_smb"]["password_set"] is True

    binding = db_session.get(IngestBinding, "movie_binding")
    assert binding is not None
    assert binding.source_smb_json["password"] == "source-secret"

    list_response = client.get("/ingest/bindings")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert list_response.json()["results"][0]["id"] == "movie_binding"


def test_update_ingest_binding_keeps_saved_password_when_blank(db_session: Session) -> None:
    client = make_client(db_session)
    assert client.post("/ingest/bindings/create", json=binding_payload()).status_code == 200
    update_payload = binding_payload()
    update_payload.pop("id")
    update_payload["name"] = "电影导入更新"
    update_payload["source_smb"]["password"] = ""
    update_payload["target_smb"]["password"] = None

    response = client.post("/ingest/bindings/movie_binding/update", json=update_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "电影导入更新"
    assert body["source_smb"]["password_set"] is True
    binding = db_session.get(IngestBinding, "movie_binding")
    assert binding.source_smb_json["password"] == "source-secret"
    assert binding.target_smb_json["password"] == "target-secret"


def test_enable_disable_and_test_ingest_binding(db_session: Session) -> None:
    client = make_client(db_session)
    assert client.post("/ingest/bindings/create", json=binding_payload()).status_code == 200

    disable_response = client.post("/ingest/bindings/movie_binding/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    enable_response = client.post("/ingest/bindings/movie_binding/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True

    test_response = client.post("/ingest/bindings/movie_binding/test")
    assert test_response.status_code == 200
    assert test_response.json() == {"ok": True, "source_ok": False, "target_ok": False, "error_code": None, "error_message": None}


def test_ingest_binding_rejects_unsafe_paths(db_session: Session) -> None:
    client = make_client(db_session)
    payload = binding_payload()
    payload["source_smb"]["base_path"] = "/../secret"

    response = client.post("/ingest/bindings/create", json=payload)

    assert response.status_code == 422


def test_missing_ingest_binding_returns_404(db_session: Session) -> None:
    client = make_client(db_session)

    response = client.get("/ingest/bindings/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "导入绑定不存在。"


def test_scan_ingest_sources_records_discovered_files(db_session: Session) -> None:
    client = make_client(db_session)
    assert client.post("/ingest/bindings/create", json=binding_payload()).status_code == 200

    async def fake_list_dir(_binding: IngestBinding, path: str) -> list[dict]:
        if path == "":
            return [
                {"name": "Movie.mkv", "path": "Movie.mkv", "is_dir": False, "size": 10, "modified_at": "100"},
                {"name": "Show", "path": "Show", "is_dir": True, "size": None, "modified_at": "100"},
            ]
        if path == "Show":
            return [{"name": "E01.mkv", "path": "Show/E01.mkv", "is_dir": False, "size": 20, "modified_at": "101"}]
        return []

    ingest_service._list_dir_override = fake_list_dir
    try:
        response = client.post("/ingest/scan", json={})
    finally:
        ingest_service._list_dir_override = None

    assert response.status_code == 200
    body = response.json()
    assert body["scanned_bindings"] == 1
    assert body["discovered_count"] == 2
    assert body["stable_count"] == 0
    assert {item["source_path"] for item in body["results"]} == {"Movie.mkv", "Show/E01.mkv"}
    assert db_session.query(IngestSeenFile).count() == 2

    list_response = client.get("/ingest/discovered")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 2


def test_scan_marks_file_stable_after_unchanged_interval(db_session: Session) -> None:
    client = make_client(db_session)
    assert client.post("/ingest/bindings/create", json=binding_payload()).status_code == 200
    assert client.post("/ingest/config/save", json={"stable_seconds": 5}).status_code == 200

    async def fake_list_dir(_binding: IngestBinding, _path: str) -> list[dict]:
        return [{"name": "Movie.mkv", "path": "Movie.mkv", "is_dir": False, "size": 10, "modified_at": "100"}]

    ingest_service._list_dir_override = fake_list_dir
    try:
        first_response = client.post("/ingest/scan", json={"binding_id": "movie_binding"})
        assert first_response.status_code == 200
        db_session.execute(text("update ingest_seen_files set updated_at = '2026-05-07 00:00:01' where source_path = 'Movie.mkv'"))
        db_session.commit()
        second_response = client.post("/ingest/scan", json={"binding_id": "movie_binding"})
    finally:
        ingest_service._list_dir_override = None

    assert second_response.status_code == 200
    body = second_response.json()
    assert body["discovered_count"] == 0
    assert body["stable_count"] == 1
    assert body["results"][0]["status"] == "stable"


def test_create_ingest_tasks_from_stable_files(db_session: Session) -> None:
    client = make_client(db_session)
    assert client.post("/ingest/bindings/create", json=binding_payload()).status_code == 200
    binding = db_session.get(IngestBinding, "movie_binding")
    seen = IngestSeenFile(
        id="seen_stable",
        binding_id=binding.id,
        source_fingerprint="fingerprint_stable",
        source_path="Movie/Movie.mkv",
        source_size=100,
        source_mtime="100",
        status="stable",
    )
    db_session.add(seen)
    db_session.commit()

    response = client.post("/ingest/tasks/create", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["created_count"] == 1
    assert body["skipped_count"] == 0
    task_id = body["tasks"][0]["id"]
    assert body["tasks"][0]["mode"] == "ingest"
    assert body["tasks"][0]["link_id"] is None
    assert body["tasks"][0]["source_path"] == "Movie/Movie.mkv"
    assert body["tasks"][0]["target_path"] == "Movie/Movie.mkv"
    task = db_session.get(TransferTask, task_id)
    assert task.source_config_snapshot["password"] == "source-secret"
    assert task.storage_config_snapshot["password"] == "target-secret"
    transfer_file = db_session.query(TransferFile).filter(TransferFile.task_id == task_id).one()
    assert transfer_file.cloud_path == "Movie/Movie.mkv"
    assert transfer_file.temp_path == "Movie/Movie.mkv.downloading"
    db_session.refresh(seen)
    assert seen.status == "queued"
    assert seen.task_id == task_id


def test_create_ingest_tasks_is_idempotent(db_session: Session) -> None:
    client = make_client(db_session)
    assert client.post("/ingest/bindings/create", json=binding_payload()).status_code == 200
    db_session.add(
        IngestSeenFile(
            id="seen_stable",
            binding_id="movie_binding",
            source_fingerprint="fingerprint_stable",
            source_path="Movie.mkv",
            source_size=100,
            source_mtime="100",
            status="stable",
        )
    )
    db_session.commit()

    first_response = client.post("/ingest/tasks/create", json={})
    second_response = client.post("/ingest/tasks/create", json={})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["created_count"] == 1
    assert second_response.json()["created_count"] == 0
    assert db_session.query(TransferTask).count() == 1
