import os
import platform
from types import SimpleNamespace

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
