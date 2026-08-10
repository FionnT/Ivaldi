from types import SimpleNamespace

import pytest

from ivaldi.shared.uv import install_uv, resolve_release
from ivaldi.types.enums import UV_ARTIFACTS


@pytest.mark.parametrize(
    ("system", "machine", "libc", "expected"),
    [
        ("Darwin", "x86_64", ("", ""), UV_ARTIFACTS.MACOS_INTEL),
        ("Windows", "amd64", ("", ""), UV_ARTIFACTS.WINDOWS_X64),
        ("Linux", "aarch64", ("musl", "1.2"), UV_ARTIFACTS.LINUX_MUSL_ARM64),
        ("Linux", "x86_64", ("glibc", "2.40"), UV_ARTIFACTS.LINUX_X64),
    ],
)
def test_resolve_release_for_supported_platforms(monkeypatch, system, machine, libc, expected):
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: system)
    monkeypatch.setattr("ivaldi.shared.uv.platform.machine", lambda: machine)
    monkeypatch.setattr("ivaldi.shared.uv.platform.libc_ver", lambda: libc)

    assert resolve_release() == expected


@pytest.mark.parametrize(("system", "machine"), [("Plan9", "x86_64"), ("Darwin", "mips")])
def test_resolve_release_rejects_unsupported_platform(monkeypatch, system, machine):
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: system)
    monkeypatch.setattr("ivaldi.shared.uv.platform.machine", lambda: machine)
    with pytest.raises(RuntimeError, match=f"{system} on {machine.upper()}"):
        resolve_release()


class Response:
    def __init__(self, chunks=(b"archive",), content_length="7"):
        self.chunks = chunks
        self.headers = {} if content_length is None else {"content-length": content_length}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield from self.chunks


def make_uv_settings(tmp_path):
    app = tmp_path / "app"
    bin_directory = app / "bin"
    app.mkdir()
    bin_directory.mkdir()
    return SimpleNamespace(
        uv=SimpleNamespace(repo="https://example.test/releases", version="1.2.3"),
        dirs=SimpleNamespace(app=app, bin=bin_directory),
        bin=SimpleNamespace(uv=None, uvx=None),
    )


def test_install_uv_downloads_extracts_and_records_executables(tmp_path, monkeypatch):
    settings = make_uv_settings(tmp_path)
    captured = {}
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr(
        "ivaldi.shared.uv.requests.get",
        lambda url, stream: captured.update(url=url, stream=stream) or Response(),
    )
    monkeypatch.setattr(
        "ivaldi.shared.uv.extract",
        lambda location, destination: captured.update(location=location, destination=destination),
    )
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Linux")

    install_uv(settings)

    assert captured["url"].endswith("/1.2.3/uv-x86_64-unknown-linux-gnu.tar.gz")
    assert captured["stream"] is True
    assert captured["location"].read_bytes() == b"archive"
    assert captured["destination"] == settings.dirs.bin
    assert settings.bin.uv == settings.dirs.bin / "uv"
    assert settings.bin.uvx == settings.dirs.bin / "uvx"


def test_install_uv_sets_windows_executable_suffix(tmp_path, monkeypatch):
    settings = make_uv_settings(tmp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.WINDOWS_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", lambda *args, **kwargs: Response())
    monkeypatch.setattr("ivaldi.shared.uv.extract", lambda **kwargs: None)
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Windows")

    install_uv(settings)

    assert settings.bin.uv.name == "uv.exe"
    assert settings.bin.uvx.name == "uvx.exe"


def test_install_uv_rejects_missing_content_length(tmp_path, monkeypatch):
    settings = make_uv_settings(tmp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", lambda *args, **kwargs: Response(content_length=None))

    with pytest.raises(ValueError, match="empty content-length"):
        install_uv(settings)


def test_install_uv_cleans_temporary_download_after_failure(tmp_path, monkeypatch):
    settings = make_uv_settings(tmp_path)

    class BrokenResponse(Response):
        def iter_content(self, chunk_size):
            raise OSError("download failed")
            yield

    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", lambda *args, **kwargs: BrokenResponse())

    with pytest.raises(OSError, match="download failed"):
        install_uv(settings)
    assert list(settings.dirs.app.iterdir()) == [settings.dirs.bin]
