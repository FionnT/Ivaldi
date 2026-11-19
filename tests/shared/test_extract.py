import tarfile
import zipfile

import pytest

from ivaldi.shared.extract import extract


def test_extract_tar_archive_moves_files_to_destination(temp_path):
    source = temp_path / "tool"
    source.mkdir()
    (source / "uv").write_text("binary", encoding="utf-8")
    archive = temp_path / "tool.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(source, arcname="tool")
    for item in source.iterdir():
        item.unlink()
    source.rmdir()

    destination = temp_path / "bin"
    extract(archive, destination)

    assert (destination / "uv").read_text(encoding="utf-8") == "binary"
    assert not archive.exists()
    assert not source.exists()


def test_extract_zip_archive_moves_files_to_destination(temp_path):
    archive = temp_path / "tool.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("tool/uv", "binary")

    destination = temp_path / "bin"
    extract(archive, destination)

    assert (destination / "uv").read_text(encoding="utf-8") == "binary"
    assert not archive.exists()


def test_extract_zip_archive_moves_root_files_to_destination(temp_path):
    archive = temp_path / "tool.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("uv.exe", "uv")
        zipped.writestr("uvx.exe", "uvx")

    destination = temp_path / "bin"
    extract(archive, destination)

    assert (destination / "uv.exe").read_text(encoding="utf-8") == "uv"
    assert (destination / "uvx.exe").read_text(encoding="utf-8") == "uvx"
    assert not archive.exists()


def test_extract_rejects_unknown_archive(temp_path):
    archive = temp_path / "tool.bin"
    archive.touch()
    with pytest.raises(ValueError, match="Unsupported archive"):
        extract(archive, temp_path / "bin")
