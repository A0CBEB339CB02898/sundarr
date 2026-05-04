from pathlib import Path

import pytest

from sundarr.app.storage import LocalWriter


@pytest.fixture()
def local_writer(tmp_path: Path) -> LocalWriter:
    return LocalWriter(tmp_path / "storage")


@pytest.mark.anyio
async def test_local_writer_appends_checks_size_and_renames(local_writer: LocalWriter) -> None:
    temp_path = "Movies/Movie.mkv.downloading"
    final_path = "Movies/Movie.mkv"

    file = await local_writer.open_append(temp_path)
    with file:
        file.write(b"0123")

    file = await local_writer.open_append(temp_path)
    with file:
        file.write(b"456")

    assert await local_writer.exists(temp_path) is True
    assert await local_writer.size(temp_path) == 7

    await local_writer.rename(temp_path, final_path)

    assert await local_writer.exists(temp_path) is False
    assert await local_writer.exists(final_path) is True
    assert await local_writer.size(final_path) == 7


@pytest.mark.anyio
async def test_local_writer_does_not_overwrite_existing_target(local_writer: LocalWriter) -> None:
    first = await local_writer.open_append("Movies/Existing.mkv")
    with first:
        first.write(b"old")
    second = await local_writer.open_append("Movies/New.mkv.downloading")
    with second:
        second.write(b"new")

    with pytest.raises(ValueError, match="TARGET_EXISTS"):
        await local_writer.rename("Movies/New.mkv.downloading", "Movies/Existing.mkv")


@pytest.mark.anyio
async def test_local_writer_remove_rejects_root(local_writer: LocalWriter) -> None:
    with pytest.raises(ValueError, match="STORAGE_REMOVE_ROOT_FORBIDDEN"):
        await local_writer.remove("")


@pytest.mark.anyio
async def test_local_writer_rejects_path_traversal(local_writer: LocalWriter) -> None:
    with pytest.raises(ValueError, match="STORAGE_PATH_OUTSIDE_ROOT"):
        await local_writer.exists("../outside")

    with pytest.raises(ValueError, match="STORAGE_PATH_OUTSIDE_ROOT"):
        await local_writer.open_append("..\\outside")
