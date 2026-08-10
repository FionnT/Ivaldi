from types import SimpleNamespace

import pytest

from ivaldi import application, main


def test_main_dispatches_run_and_forwards_only_application_arguments(monkeypatch):
    captured = {}

    def run(location, args):
        captured["args"] = args
        return 17

    monkeypatch.setattr("ivaldi._run", run)

    result = main(["run", "--verbose", "--output", "some file.txt"])

    assert result == 17
    assert captured["args"] == ["--verbose", "--output", "some file.txt"]


def test_application_installs_on_first_run_then_forwards_arguments(monkeypatch, tmp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin=False))
    calls = []
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi._install", lambda location, executable=None: calls.append(("install", location, executable)))
    monkeypatch.setattr("ivaldi._run", lambda location, args: calls.append(("run", location, args)) or 19)

    result = application(["--flag", "some value"], executable=tmp_path / "launcher")

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


def test_application_requests_sudo_for_the_install_phase(monkeypatch, tmp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin="install"))
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi.is_admin", lambda: False)
    monkeypatch.setattr("ivaldi._install", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("local install")))

    with pytest.raises(SystemExit, match="sudo"):
        application(["--flag"], executable=tmp_path / "launcher")


def test_application_requests_sudo_before_install_and_run_for_admin_true(monkeypatch, tmp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin=True))
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi.is_admin", lambda: False)
    monkeypatch.setattr("ivaldi._install", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("local install")))
    monkeypatch.setattr("ivaldi._run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("local run")))

    with pytest.raises(SystemExit, match="sudo"):
        application(["launch"], executable=tmp_path / "launcher")


def test_install_only_admin_mode_exits_after_privileged_install(monkeypatch, tmp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(admin="install"))
    calls = []
    monkeypatch.setattr("ivaldi.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.is_installed", lambda value: False)
    monkeypatch.setattr("ivaldi.is_admin", lambda: True)
    monkeypatch.setattr("ivaldi._install", lambda *args, **kwargs: calls.append("install"))
    monkeypatch.setattr("ivaldi._run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("privileged run")))

    assert application([], executable=tmp_path / "launcher") == 0
    assert calls == ["install"]
