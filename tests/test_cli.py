import runpy
import sys
from types import SimpleNamespace

import pytest

from ivaldi import application, main


def test_main_prints_help_for_no_arguments(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ivaldi"])

    assert main() == 0
    assert "Usage: ivaldi" in capsys.readouterr().out


def test_main_dispatches_build_and_install(monkeypatch):
    calls = []
    monkeypatch.setattr("ivaldi._build", lambda location: calls.append("build"))
    monkeypatch.setattr("ivaldi._install", lambda location: calls.append("install"))

    assert main(["build"]) == 0
    assert main(["install"]) == 0
    assert calls == ["build", "install"]


def test_main_rejects_unknown_commands_and_command_arguments():
    with pytest.raises(SystemExit, match="Unknown command"):
        main(["unknown"])
    with pytest.raises(SystemExit, match="does not accept arguments"):
        main(["build", "extra"])


def test_console_script_wrappers(monkeypatch):
    import ivaldi

    calls = []
    monkeypatch.setattr(ivaldi, "_build", lambda location: calls.append("build"))
    monkeypatch.setattr(ivaldi, "_install", lambda location: calls.append("install"))
    monkeypatch.setattr(ivaldi, "_run", lambda location: calls.append("run") or 5)

    ivaldi.build()
    ivaldi.install()
    assert ivaldi.run() == 5
    assert calls == ["build", "install", "run"]


def test_module_entrypoint_exits_with_application_status(monkeypatch):
    import ivaldi

    monkeypatch.setattr(ivaldi, "application", lambda: 12)
    with pytest.raises(SystemExit) as raised:
        runpy.run_module("ivaldi.__main__", run_name="__main__")
    assert raised.value.code == 12


def test_main_dispatches_run_and_forwards_only_application_arguments(monkeypatch):
    captured = {}

    def run(location, args):
        captured["args"] = args
        return 17

    monkeypatch.setattr("ivaldi._run", run)

    result = main(["run", "--verbose", "--output", "some file.txt"])

    assert result == 17
    assert captured["args"] == ["--verbose", "--output", "some file.txt"]


def test_application_installs_on_first_run_then_forwards_arguments(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin=False))
    calls = []
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi._install", lambda location, executable=None: calls.append(("install", location, executable)))
    monkeypatch.setattr("ivaldi._run", lambda location, args: calls.append(("run", location, args)) or 19)

    result = application(["--flag", "some value"], executable=temp_path / "launcher")

    assert result == 19
    assert calls[0][0] == "install"
    assert calls[1][0] == "run"
    assert calls[1][2] == ["--flag", "some value"]


def test_application_skips_install_for_an_existing_runtime(monkeypatch):
    settings = SimpleNamespace(platform=SimpleNamespace(admin=False))
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: True)
    monkeypatch.setattr("ivaldi._install", lambda location: (_ for _ in ()).throw(AssertionError("installed again")))
    monkeypatch.setattr("ivaldi._run", lambda location, args: 7)

    assert application([]) == 7


@pytest.mark.parametrize("installed", [False, True])
def test_application_uninstalls_without_installing_or_running(monkeypatch, temp_path, installed):
    settings = SimpleNamespace(platform=SimpleNamespace(admin=False))
    calls = []
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: installed)
    monkeypatch.setattr("ivaldi._install", lambda *args, **kwargs: calls.append("install"))
    monkeypatch.setattr("ivaldi._run", lambda *args, **kwargs: calls.append("run"))
    monkeypatch.setattr("ivaldi._uninstall", lambda location: calls.append("uninstall"))

    assert application(["--uninstall"], executable=temp_path / "launcher") == 0
    assert calls == ["uninstall"]


def test_application_requests_install_privileges_for_uninstall(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin="install"))
    launcher = temp_path / "launcher"
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_admin", lambda: False)
    monkeypatch.setattr("ivaldi._uninstall", lambda location: (_ for _ in ()).throw(AssertionError("local uninstall")))
    monkeypatch.setattr("ivaldi.run_elevated", lambda executable, args: (executable, args))

    assert application(["--uninstall"], executable=launcher) == (launcher.resolve(), ["--uninstall"])


def test_application_does_not_forward_uninstall_with_other_arguments(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin=False))
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi._uninstall", lambda location: (_ for _ in ()).throw(AssertionError("ambiguous uninstall")))
    monkeypatch.setattr("ivaldi._run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("forwarded uninstall")))

    with pytest.raises(SystemExit, match="does not accept other arguments"):
        application(["launch", "--uninstall"], executable=temp_path / "launcher")


def test_application_requests_sudo_for_the_install_phase(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin="install"))
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi.is_admin", lambda: False)
    monkeypatch.setattr("ivaldi._install", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("local install")))

    with pytest.raises(SystemExit, match="sudo"):
        application(["--flag"], executable=temp_path / "launcher")


def test_application_requests_sudo_before_install_and_run_for_admin_true(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin=True))
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi.is_admin", lambda: False)
    monkeypatch.setattr("ivaldi._install", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("local install")))
    monkeypatch.setattr("ivaldi._run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("local run")))

    with pytest.raises(SystemExit, match="sudo"):
        application(["launch"], executable=temp_path / "launcher")


def test_install_only_admin_mode_exits_after_privileged_install(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin="install"))
    calls = []
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi.is_admin", lambda: True)
    monkeypatch.setattr("ivaldi._install", lambda *args, **kwargs: calls.append("install"))
    monkeypatch.setattr("ivaldi._run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("privileged run")))

    assert application([], executable=temp_path / "launcher") == 0
    assert calls == ["install"]


def test_application_elevates_an_existing_install_for_run(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin="run"))
    launcher = temp_path / "launcher"
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: True)
    monkeypatch.setattr("ivaldi.is_admin", lambda: False)
    monkeypatch.setattr("ivaldi.run_elevated", lambda executable, args: (executable, args))

    assert application(["arg"], executable=launcher) == (launcher.resolve(), ["arg"])
