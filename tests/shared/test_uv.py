import hashlib
from types import SimpleNamespace

import pytest
import requests

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
    def __init__(self, chunks=(b"archive",), content_length="7", status_code=200, text=""):
        self.chunks = chunks
        self.status_code = status_code
        self.text = text
        self.headers = {} if content_length is None else {"content-length": content_length}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def iter_content(self, chunk_size):
        yield from self.chunks


def fake_get(response, checksum_response=None):
    """Serve ``response`` for the archive and a missing checksum (404) unless one is given."""
    checksum_response = checksum_response or Response(status_code=404)
    return lambda url, **kwargs: checksum_response if url.endswith(".sha256") else response


def make_uv_settings(temp_path):
    app = temp_path / "app"
    bin_directory = app / "bin"
    app.mkdir()
    bin_directory.mkdir()
    return SimpleNamespace(
        uv=SimpleNamespace(repo="https://example.test/releases", version="1.2.3"),
        dirs=SimpleNamespace(app=app, bin=bin_directory),
        bin=SimpleNamespace(uv=None, uvx=None),
    )


def test_install_uv_downloads_extracts_and_records_executables(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    captured = {}
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr(
        "ivaldi.shared.uv.requests.get",
        lambda url, stream=False, timeout=None: captured.update(url=url, stream=stream, timeout=timeout) or Response() if not url.endswith(".sha256") else Response(status_code=404),
    )

    def extract(location, destination):
        captured.update(location=location, destination=destination)
        (destination / "uv").touch()
        (destination / "uvx").touch()

    monkeypatch.setattr("ivaldi.shared.uv.extract", extract)
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Linux")

    install_uv(settings)

    assert captured["url"].endswith("/1.2.3/uv-x86_64-unknown-linux-gnu.tar.gz")
    assert captured["stream"] is True
    assert captured["timeout"] is not None
    assert captured["location"].read_bytes() == b"archive"
    assert captured["destination"] == settings.dirs.bin
    assert settings.bin.uv == settings.dirs.bin / "uv"
    assert settings.bin.uvx == settings.dirs.bin / "uvx"


def test_install_uv_sets_windows_executable_suffix(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.WINDOWS_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(Response()))

    def extract(**kwargs):
        (kwargs["destination"] / "uv.exe").touch()
        (kwargs["destination"] / "uvx.exe").touch()

    monkeypatch.setattr("ivaldi.shared.uv.extract", extract)
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Windows")

    install_uv(settings)

    assert settings.bin.uv.name == "uv.exe"
    assert settings.bin.uvx.name == "uvx.exe"


def test_install_uv_rejects_archive_without_executables(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.WINDOWS_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(Response()))
    monkeypatch.setattr("ivaldi.shared.uv.extract", lambda **kwargs: None)
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Windows")

    with pytest.raises(FileNotFoundError, match=r"uv\.exe, uvx\.exe"):
        install_uv(settings)


def test_install_uv_accepts_missing_content_length(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(Response(content_length=None)))
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Linux")

    def extract(location, destination):
        (destination / "uv").touch()
        (destination / "uvx").touch()

    monkeypatch.setattr("ivaldi.shared.uv.extract", extract)
    install_uv(settings)


def test_install_uv_rejects_truncated_download(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(Response(content_length="100")))
    monkeypatch.setattr("ivaldi.shared.uv.time.sleep", lambda _: None)

    with pytest.raises(OSError, match="truncated"):
        install_uv(settings)
    assert list(settings.dirs.app.iterdir()) == [settings.dirs.bin]


def test_install_uv_rejects_empty_download(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(Response(chunks=(), content_length="0")))

    with pytest.raises(ValueError, match="empty file"):
        install_uv(settings)


def test_install_uv_verifies_published_checksum(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    good = hashlib.sha256(b"archive").hexdigest()
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Linux")

    def extract(location, destination):
        (destination / "uv").touch()
        (destination / "uvx").touch()

    monkeypatch.setattr("ivaldi.shared.uv.extract", extract)
    monkeypatch.setattr(
        "ivaldi.shared.uv.requests.get",
        fake_get(Response(), Response(text=f"{good}  uv-x86_64-unknown-linux-gnu.tar.gz\n")),
    )
    install_uv(settings)

    (temp_path / "second").mkdir()
    bad = make_uv_settings(temp_path / "second")
    monkeypatch.setattr(
        "ivaldi.shared.uv.requests.get",
        fake_get(Response(), Response(text=f"{'0' * 64}  uv-x86_64-unknown-linux-gnu.tar.gz\n")),
    )
    with pytest.raises(ValueError, match="Checksum mismatch"):
        install_uv(bad)
    assert list(bad.dirs.app.iterdir()) == [bad.dirs.bin]


def test_install_uv_rejects_malformed_checksum(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(Response(), Response(text="nonsense")))

    with pytest.raises(RuntimeError, match="malformed"):
        install_uv(settings)


def test_install_uv_retries_transient_failures_but_not_client_errors(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)
    attempts = []
    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.platform.system", lambda: "Linux")
    monkeypatch.setattr("ivaldi.shared.uv.time.sleep", lambda _: None)

    def extract(location, destination):
        (destination / "uv").touch()
        (destination / "uvx").touch()

    monkeypatch.setattr("ivaldi.shared.uv.extract", extract)

    def flaky(url, **kwargs):
        if url.endswith(".sha256"):
            return Response(status_code=404)
        attempts.append(url)
        if len(attempts) < 3:
            raise requests.ConnectionError("reset")
        return Response()

    monkeypatch.setattr("ivaldi.shared.uv.requests.get", flaky)
    install_uv(settings)
    assert len(attempts) == 3

    attempts.clear()
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(Response(status_code=403)))
    with pytest.raises(requests.HTTPError):
        install_uv(settings)


def test_install_uv_cleans_temporary_download_after_failure(temp_path, monkeypatch):
    settings = make_uv_settings(temp_path)

    class BrokenResponse(Response):
        def iter_content(self, chunk_size):
            raise OSError("download failed")
            yield

    monkeypatch.setattr("ivaldi.shared.uv.resolve_release", lambda: UV_ARTIFACTS.LINUX_X64)
    monkeypatch.setattr("ivaldi.shared.uv.requests.get", fake_get(BrokenResponse()))
    monkeypatch.setattr("ivaldi.shared.uv.time.sleep", lambda _: None)

    with pytest.raises(OSError, match="download failed"):
        install_uv(settings)
    assert list(settings.dirs.app.iterdir()) == [settings.dirs.bin]
