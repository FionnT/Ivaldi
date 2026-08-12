import os
import shutil
from types import SimpleNamespace

import pytest

from ivaldi.shared.alias import get_shell_config, install_alias, remove_command, uninstall_alias


def make_settings(temp_path, alias="my-command", add_to_path=True):
    return SimpleNamespace(
        platform=SimpleNamespace(alias=alias, add_to_path=add_to_path),
        dirs=SimpleNamespace(exec=temp_path / "bin"),
    )


def test_install_alias_adds_managed_alias_to_zshrc(temp_path, monkeypatch):
    executable = temp_path / "downloaded launcher"
    executable.write_bytes(b"launcher")
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("ivaldi.shared.alias.Path.home", lambda: temp_path)
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Darwin")

    installed = install_alias(make_settings(temp_path), executable)

    assert installed == temp_path / "bin/my-command"
    assert installed.read_bytes() == b"launcher"
    assert os.access(installed, os.X_OK)
    assert (temp_path / ".zshrc").read_text(encoding="utf-8") == (f"# >>> ivaldi alias: my-command >>>\nalias my-command={installed.resolve()}\n# <<< ivaldi alias: my-command <<<\n")


def test_install_alias_replaces_its_existing_managed_block(temp_path, monkeypatch):
    first = temp_path / "first"
    second = temp_path / "second"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    config = temp_path / ".zshrc"
    config.write_text("export KEEP=true\n", encoding="utf-8")
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr("ivaldi.shared.alias.Path.home", lambda: temp_path)
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Darwin")

    install_alias(make_settings(temp_path), first)
    install_alias(make_settings(temp_path), second)

    content = config.read_text(encoding="utf-8")
    assert content.count("# >>> ivaldi alias: my-command >>>") == 1
    assert str(temp_path / "bin/my-command") in content
    assert (temp_path / "bin/my-command").read_bytes() == b"second"
    assert "export KEEP=true" in content


@pytest.mark.parametrize(
    ("shell", "system", "relative", "syntax"),
    [
        ("/bin/zsh", "Darwin", ".zshrc", "posix"),
        ("/bin/bash", "Darwin", ".bash_profile", "posix"),
        ("/bin/bash", "Linux", ".bashrc", "posix"),
        ("/opt/homebrew/bin/fish", "Darwin", ".config/fish/config.fish", "fish"),
        ("/bin/unknown", "Linux", ".profile", "posix"),
    ],
)
def test_get_shell_config_selects_applicable_startup_file(temp_path, monkeypatch, shell, system, relative, syntax):
    monkeypatch.setenv("SHELL", shell)
    monkeypatch.setattr("ivaldi.shared.alias.Path.home", lambda: temp_path)
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: system)
    assert get_shell_config() == (temp_path / relative, syntax)


def test_install_alias_uses_fish_syntax(temp_path, monkeypatch):
    executable = temp_path / "launcher"
    executable.touch()
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    monkeypatch.setattr("ivaldi.shared.alias.Path.home", lambda: temp_path)
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Linux")

    installed = install_alias(make_settings(temp_path), executable)

    assert f"alias my-command {installed.resolve()}" in (temp_path / ".config/fish/config.fish").read_text(encoding="utf-8")


def test_install_alias_does_nothing_when_add_to_path_is_disabled(temp_path):
    settings = make_settings(temp_path, add_to_path=False)
    assert install_alias(settings, temp_path / "launcher") is None


def test_install_alias_rejects_path_alias_and_missing_launcher(temp_path):
    with pytest.raises(ValueError, match="command name"):
        install_alias(make_settings(temp_path, alias="bin/my-command"), temp_path / "launcher")
    with pytest.raises(FileNotFoundError, match="launcher executable"):
        install_alias(make_settings(temp_path), temp_path / "launcher")


def test_install_alias_copies_windows_launcher_with_exe_suffix(temp_path, monkeypatch):
    executable = temp_path / "launcher"
    executable.touch()
    destination = temp_path / "bin"
    destination.mkdir()
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Windows")

    installed = install_alias(make_settings(temp_path), executable)

    assert installed == destination / "my-command.exe"
    assert installed.is_file()


def test_install_alias_returns_existing_windows_destination(temp_path, monkeypatch):
    destination = temp_path / "bin"
    destination.mkdir()
    executable = destination / "my-command.exe"
    executable.touch()
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Windows")

    assert install_alias(make_settings(temp_path, alias="my-command.exe"), executable) == executable


def test_install_alias_cleans_windows_temporary_file_after_copy_failure(monkeypatch, temp_path):
    executable = temp_path / "launcher"
    executable.touch()
    destination = temp_path / "bin"
    destination.mkdir()
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Windows")
    monkeypatch.setattr(shutil, "copy2", lambda *args: (_ for _ in ()).throw(OSError("copy failed")))

    with pytest.raises(OSError, match="copy failed"):
        install_alias(make_settings(temp_path), executable)
    assert list(destination.iterdir()) == []


def test_uninstall_alias_removes_command_and_managed_shell_blocks(temp_path, monkeypatch):
    settings = make_settings(temp_path)
    command = settings.dirs.exec / "my-command"
    command.parent.mkdir()
    command.touch()
    zshrc = temp_path / ".zshrc"
    zshrc.write_text(
        f"export KEEP=true\n# >>> ivaldi alias: my-command >>>\nalias my-command={command}\n# <<< ivaldi alias: my-command <<<\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("ivaldi.shared.alias.Path.home", lambda: temp_path)
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Linux")

    assert uninstall_alias(settings) == command
    assert not command.exists()
    assert zshrc.read_text(encoding="utf-8") == "export KEEP=true\n"

    assert uninstall_alias(settings) == command


def test_uninstall_alias_does_nothing_when_add_to_path_is_disabled(temp_path):
    assert uninstall_alias(make_settings(temp_path, add_to_path=False)) is None


def test_remove_command_defers_deleting_a_running_windows_launcher(temp_path, monkeypatch):
    command = temp_path / "my-command.exe"
    command.touch()
    started = {}
    original_unlink = type(command).unlink

    def locked_unlink(path, *args, **kwargs):
        if path == command:
            raise PermissionError("in use")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(type(command), "unlink", locked_unlink)
    monkeypatch.setattr("ivaldi.shared.alias.platform.system", lambda: "Windows")
    monkeypatch.setattr("ivaldi.shared.alias.subprocess.Popen", lambda args, **kwargs: started.update(args=args, kwargs=kwargs))

    remove_command(command)

    assert started["args"][:3] == ["cmd.exe", "/d", "/c"]
    cleanup = type(command)(started["args"][3])
    assert str(command) in cleanup.read_text(encoding="utf-8")
    original_unlink(cleanup)
