import pytest

from sundarr.app.storage import SmbConfig, SmbWriter


@pytest.fixture()
def smb_writer() -> SmbWriter:
    return SmbWriter(
        SmbConfig(
            host="fnos.local",
            share="media",
            username="sundarr",
            password="secret",
            base_path="/Archive",
        )
    )


def test_smb_writer_builds_unc_path_under_base_path(smb_writer: SmbWriter) -> None:
    assert smb_writer._build_unc_path("Movies/Movie.mkv") == "\\\\fnos.local\\media\\Archive\\Movies\\Movie.mkv"


def test_smb_writer_rejects_path_traversal(smb_writer: SmbWriter) -> None:
    with pytest.raises(ValueError, match="SMB_PATH_OUTSIDE_ROOT"):
        smb_writer._build_unc_path("../outside")

    with pytest.raises(ValueError, match="SMB_PATH_OUTSIDE_ROOT"):
        smb_writer._build_unc_path("Movies/../../outside")


def test_smb_writer_rejects_windows_drive_path(smb_writer: SmbWriter) -> None:
    with pytest.raises(ValueError, match="SMB_PATH_INVALID"):
        smb_writer._build_unc_path("C:/Windows")


@pytest.mark.anyio
async def test_smb_writer_reports_missing_client(smb_writer: SmbWriter, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_client():
        raise ValueError("SMB_CLIENT_NOT_INSTALLED")

    monkeypatch.setattr(smb_writer, "_require_smbclient", missing_client)

    with pytest.raises(ValueError, match="SMB_CLIENT_NOT_INSTALLED"):
        await smb_writer.exists("Movies/Movie.mkv")
