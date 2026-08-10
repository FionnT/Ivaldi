import os
import platform
import shutil
from types import SimpleNamespace

import pytest

from ivaldi.shared.alias import install_alias


def test_install_alias_copies_launcher_under_configured_command_name(tmp_path):
    executable = tmp_path / "downloaded-launcher"
    executable.write_bytes(b"launcher")
    destination_dir = tmp_path / "bin"
    destination_dir.mkdir()
    settings = SimpleNamespace(
        platform=SimpleNamespace(alias="my-command", add_to_path=True),
        dirs=SimpleNamespace(exec=destination_dir),
    )

    installed = install_alias(settings, executable)

    suffix = ".exe" if platform.system() == "Windows" else ""
    assert installed == destination_dir / f"my-command{suffix}"
    assert installed.read_bytes() == b"launcher"
    if os.name != "nt":
        assert os.access(installed, os.X_OK)


def test_install_alias_does_nothing_when_add_to_path_is_disabled(tmp_path):
    settings = SimpleNamespace(
        platform=SimpleNamespace(alias="my-command", add_to_path=False),
        dirs=SimpleNamespace(exec=tmp_path / "bin"),
    )

    assert install_alias(settings, tmp_path / "launcher") is None
    assert not settings.dirs.exec.exists()


def test_install_alias_rejects_path_alias_and_missing_launcher(tmp_path):
    settings = SimpleNamespace(
        platform=SimpleNamespace(alias="bin/my-command", add_to_path=True),
        dirs=SimpleNamespace(exec=tmp_path),
    )
    with pytest.raises(ValueError, match="command name"):
        install_alias(settings, tmp_path / "launcher")

    settings.platform.alias = "my-command"
    with pytest.raises(FileNotFoundError, match="launcher executable"):
        install_alias(settings, tmp_path / "launcher")


def test_install_alias_returns_existing_destination(tmp_path):
    executable = tmp_path / "my-command"
    executable.touch()
    settings = SimpleNamespace(
        platform=SimpleNamespace(alias="my-command", add_to_path=True),
        dirs=SimpleNamespace(exec=tmp_path),
    )

    assert install_alias(settings, executable) == executable


def test_install_alias_adds_windows_suffix(monkeypatch, tmp_path):
    executable = tmp_path / "launcher"
    executable.touch()
    destination = tmp_path / "bin"
    destination.mkdir()
    settings = SimpleNamespace(
        platform=SimpleNamespace(alias="my-command", add_to_path=True),
        dirs=SimpleNamespace(exec=destination),
    )
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Windows")

    assert install_alias(settings, executable).name == "my-command.exe"


def test_install_alias_cleans_temporary_file_after_copy_failure(monkeypatch, tmp_path):
    executable = tmp_path / "launcher"
    executable.touch()
    destination = tmp_path / "bin"
    destination.mkdir()
    settings = SimpleNamespace(
        platform=SimpleNamespace(alias="my-command", add_to_path=True),
        dirs=SimpleNamespace(exec=destination),
    )
    monkeypatch.setattr(shutil, "copy2", lambda *args: (_ for _ in ()).throw(OSError("copy failed")))

    with pytest.raises(OSError, match="copy failed"):
        install_alias(settings, executable)
    assert list(destination.iterdir()) == []
