import pytest

from sundarr.app.storage import SmbConfig, SmbWriter
from sundarr.app.storage.smb import SmbStorageError


@pytest.fixture()
def smb_writer() -> SmbWriter:
    return SmbWriter(
        SmbConfig(
            host="nas.example.invalid",
            share="share",
            username="sundarr",
            password="secret",
            base_path="/Archive",
        )
    )


def test_smb_writer_builds_unc_path_under_base_path(smb_writer: SmbWriter) -> None:
    assert smb_writer._build_unc_path("Movies/Movie.mkv") == "\\\\nas.example.invalid\\share\\Archive\\Movies\\Movie.mkv"


def test_smb_writer_rejects_path_traversal(smb_writer: SmbWriter) -> None:
    with pytest.raises(ValueError, match="SMB_PATH_OUTSIDE_ROOT"):
        smb_writer._build_unc_path("../outside")

    with pytest.raises(ValueError, match="SMB_PATH_OUTSIDE_ROOT"):
        smb_writer._build_unc_path("Movies/../../outside")


def test_smb_writer_rejects_windows_drive_path(smb_writer: SmbWriter) -> None:
    with pytest.raises(ValueError, match="SMB_PATH_INVALID"):
        smb_writer._build_unc_path("C:/Windows")


def test_smb_writer_registers_session(smb_writer: SmbWriter, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeSmbClient:
        def register_session(self, host: str, username: str, password: str, port: int) -> None:
            calls.append({"host": host, "username": username, "password": password, "port": port})

    monkeypatch.setattr(smb_writer, "_require_smbclient", lambda: FakeSmbClient())
    smb_writer._register_session(FakeSmbClient())

    assert calls == [{"host": "nas.example.invalid", "username": "sundarr", "password": "secret", "port": 445}]


@pytest.mark.anyio
async def test_smb_writer_reports_missing_client(smb_writer: SmbWriter, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_client():
        raise ValueError("SMB_CLIENT_NOT_INSTALLED")

    monkeypatch.setattr(smb_writer, "_require_smbclient", missing_client)

    with pytest.raises(ValueError, match="SMB_CLIENT_NOT_INSTALLED"):
        await smb_writer.exists("Movies/Movie.mkv")


@pytest.mark.anyio
async def test_smb_writer_test_connection_lists_root(smb_writer: SmbWriter, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeSmbClient:
        def listdir(self, path: str) -> list[str]:
            calls.append(path)
            return []

    monkeypatch.setattr(smb_writer, "_require_smbclient", lambda: FakeSmbClient())

    await smb_writer.test_connection()

    assert calls == ["\\\\nas.example.invalid\\share\\Archive"]


@pytest.mark.anyio
async def test_smb_writer_classifies_auth_failure(smb_writer: SmbWriter, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSmbClient:
        def listdir(self, path: str) -> list[str]:
            raise RuntimeError("STATUS_LOGON_FAILURE")

    monkeypatch.setattr(smb_writer, "_require_smbclient", lambda: FakeSmbClient())

    with pytest.raises(SmbStorageError) as exc_info:
        await smb_writer.test_connection()

    assert exc_info.value.code == "SMB_AUTH_FAILED"
    assert "密码" in exc_info.value.message


@pytest.mark.anyio
async def test_smb_writer_classifies_share_not_found(smb_writer: SmbWriter, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSmbClient:
        def listdir(self, path: str) -> list[str]:
            raise RuntimeError("STATUS_BAD_NETWORK_NAME")

    monkeypatch.setattr(smb_writer, "_require_smbclient", lambda: FakeSmbClient())

    with pytest.raises(SmbStorageError) as exc_info:
        await smb_writer.test_connection()

    assert exc_info.value.code == "SMB_SHARE_NOT_FOUND"
    assert "share" in exc_info.value.message


@pytest.mark.anyio
async def test_smb_writer_redacts_password_from_unknown_error(smb_writer: SmbWriter, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSmbClient:
        def listdir(self, path: str) -> list[str]:
            raise RuntimeError("unexpected secret failure")

    monkeypatch.setattr(smb_writer, "_require_smbclient", lambda: FakeSmbClient())

    with pytest.raises(SmbStorageError) as exc_info:
        await smb_writer.test_connection()

    assert exc_info.value.code == "SMB_CONNECT_FAILED"
    assert "secret" not in exc_info.value.message
