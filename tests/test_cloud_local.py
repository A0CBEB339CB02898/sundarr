from pathlib import Path

import pytest

from sundarr.app.cloud import LocalCloudProvider


@pytest.fixture()
def local_cloud(tmp_path: Path) -> LocalCloudProvider:
    share_root = tmp_path / "shares"
    staging_root = tmp_path / "staging"
    source_dir = share_root / "movie_share"
    source_dir.mkdir(parents=True)
    (source_dir / "Movie.mkv").write_bytes(b"0123456789")
    (source_dir / "subtitle.srt").write_text("字幕", encoding="utf-8")
    return LocalCloudProvider(staging_root=staging_root, share_root=share_root, chunk_size=4)


@pytest.mark.anyio
async def test_save_share_lists_files_and_streams(local_cloud: LocalCloudProvider) -> None:
    staging_path = await local_cloud.save_share("local://movie_share", code=None, target_dir="task_001")

    assert staging_path == "/Sundarr/_staging/task_001"

    files = await local_cloud.list_files(staging_path)
    names = {file.name for file in files}
    assert names == {"Movie.mkv", "subtitle.srt"}

    movie = next(file for file in files if file.name == "Movie.mkv")
    chunks = [chunk async for chunk in local_cloud.open_file_stream(movie.id, offset=3)]
    assert b"".join(chunks) == b"3456789"


@pytest.mark.anyio
async def test_delete_only_allows_staging_children(local_cloud: LocalCloudProvider) -> None:
    staging_path = await local_cloud.save_share("local://movie_share", code=None, target_dir="task_delete")

    await local_cloud.delete(staging_path)

    assert await local_cloud.list_files(staging_path) == []


@pytest.mark.anyio
async def test_delete_rejects_staging_root(local_cloud: LocalCloudProvider) -> None:
    with pytest.raises(ValueError, match="CLOUD_STAGING_DELETE_ROOT_FORBIDDEN"):
        await local_cloud.delete("/Sundarr/_staging")


@pytest.mark.anyio
async def test_rejects_path_traversal(local_cloud: LocalCloudProvider) -> None:
    with pytest.raises(ValueError, match="CLOUD_STAGING_PATH_OUTSIDE_ROOT"):
        await local_cloud.list_files("../outside")

    with pytest.raises(ValueError, match="LOCAL_SHARE_PATH_OUTSIDE_ROOT"):
        await local_cloud.save_share("local://../outside", code=None, target_dir="task_bad")
