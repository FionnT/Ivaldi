from types import SimpleNamespace

import pytest

from ivaldi.commands.uninstall import uninstall


def test_uninstall_removes_command_and_complete_application_tree(temp_path, monkeypatch):
    app = temp_path / "app"
    (app / "venv/bin").mkdir(parents=True)
    (app / "venv/bin/python").touch()
    settings = SimpleNamespace(platform=SimpleNamespace(location="example-app"), dirs=SimpleNamespace(app=app))
    calls = []
    monkeypatch.setattr("ivaldi.commands.uninstall.load_settings", lambda **kwargs: calls.append("load") or settings)
    monkeypatch.setattr("ivaldi.commands.uninstall.load_runtime_directories", lambda value: calls.append("directories") or value)
    monkeypatch.setattr("ivaldi.commands.uninstall.uninstall_alias", lambda value: calls.append("alias"))

    assert uninstall(temp_path) is settings
    assert calls == ["load", "directories", "alias"]
    assert not app.exists()


def test_uninstall_is_idempotent_when_nothing_is_installed(temp_path, monkeypatch):
    settings = SimpleNamespace(platform=SimpleNamespace(location="example-app"), dirs=SimpleNamespace(app=temp_path / "missing"))
    monkeypatch.setattr("ivaldi.commands.uninstall.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.commands.uninstall.load_runtime_directories", lambda value: value)
    monkeypatch.setattr("ivaldi.commands.uninstall.uninstall_alias", lambda value: None)

    assert uninstall(temp_path) is settings


@pytest.mark.parametrize("location", [".", "../shared", "/shared"])
def test_uninstall_rejects_locations_outside_an_application_subdirectory(temp_path, monkeypatch, location):
    settings = SimpleNamespace(platform=SimpleNamespace(location=location), dirs=SimpleNamespace(app=temp_path))
    monkeypatch.setattr("ivaldi.commands.uninstall.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.commands.uninstall.load_runtime_directories", lambda value: value)

    with pytest.raises(ValueError, match="relative application subdirectory"):
        uninstall(temp_path)
