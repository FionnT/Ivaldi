from pathlib import Path
from types import SimpleNamespace

import pytest

from ivaldi.commands.build import build
from ivaldi.commands.install import install


@pytest.mark.parametrize("include_wheels", [False, True])
def test_build_command_runs_the_build_pipeline(monkeypatch, temp_path, include_wheels):
    settings = SimpleNamespace(app=SimpleNamespace(build=SimpleNamespace(include_wheels=include_wheels)))
    calls = []
    monkeypatch.setattr("ivaldi.commands.build.load_settings", lambda location, build: calls.append("load") or settings)
    monkeypatch.setattr("ivaldi.commands.build.load_install_directories", lambda value: calls.append("directories") or value)
    monkeypatch.setattr("ivaldi.commands.build.prepare_build", lambda value: calls.append("prepare"))
    monkeypatch.setattr("ivaldi.commands.build.collect", lambda value: calls.append("collect"))
    monkeypatch.setattr("ivaldi.commands.build.build_project_wheel", lambda value: calls.append("wheel") or Path("app.whl"))
    monkeypatch.setattr("ivaldi.commands.build.build_all_wheels", lambda value, wheel: calls.append("dependencies"))
    monkeypatch.setattr("ivaldi.commands.build.build_executable", lambda location, value: calls.append("executable") or Path("app"))

    assert build(temp_path) == Path("app")
    expected = ["load", "directories", "prepare", "collect", "wheel"]
    if include_wheels:
        expected.append("dependencies")
    assert calls == [*expected, "executable"]


@pytest.mark.parametrize(
    ("add_to_path", "alias", "marked"),
    [(False, None, True), (True, Path("alias"), True), (True, None, False)],
)
def test_install_command_runs_pipeline_and_marks_complete(monkeypatch, temp_path, add_to_path, alias, marked):
    settings = SimpleNamespace(platform=SimpleNamespace(add_to_path=add_to_path), dirs=SimpleNamespace(app=temp_path / "app"))
    calls = []
    monkeypatch.setattr("ivaldi.commands.install.load_settings", lambda **kwargs: calls.append("load") or settings)
    monkeypatch.setattr("ivaldi.commands.install.load_install_directories", lambda value: calls.append("directories") or value)
    monkeypatch.setattr("ivaldi.commands.install.install_uv", lambda value: calls.append("uv"))
    monkeypatch.setattr("ivaldi.commands.install.install_python", lambda value: calls.append("python"))
    monkeypatch.setattr("ivaldi.commands.install.install_project", lambda value: calls.append("project"))
    monkeypatch.setattr("ivaldi.commands.install.install_alias", lambda value, executable: calls.append("alias") or alias)
    monkeypatch.setattr("ivaldi.commands.install.mark_installed", lambda value: calls.append("mark"))
    monkeypatch.setattr("ivaldi.commands.install.restore_sudo_ownership", lambda path: calls.append(("ownership", path)))

    assert install(temp_path, executable=temp_path / "launcher") is settings
    assert ("mark" in calls) is marked
    assert calls[:6] == ["load", "directories", "uv", "python", "project", "alias"]
    assert calls[-1] == ("ownership", settings.dirs.app)


def test_install_restores_ownership_after_a_partial_failure(monkeypatch, temp_path):
    settings = SimpleNamespace(platform=SimpleNamespace(add_to_path=False), dirs=SimpleNamespace(app=temp_path / "app"))
    calls = []
    monkeypatch.setattr("ivaldi.commands.install.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.commands.install.load_install_directories", lambda value: value)
    monkeypatch.setattr("ivaldi.commands.install.install_uv", lambda value: None)
    monkeypatch.setattr("ivaldi.commands.install.install_python", lambda value: (_ for _ in ()).throw(RuntimeError("failed")))
    monkeypatch.setattr("ivaldi.commands.install.restore_sudo_ownership", lambda path: calls.append(path))

    with pytest.raises(RuntimeError, match="failed"):
        install(temp_path)

    assert calls == [settings.dirs.app]
