from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from ivaldi.shared.project import get_wheel_requirement, handle_install_flags, handle_wheel, install_project, mark_installed
from ivaldi.types.enums import IVALDI
from ivaldi.types.settings import UV, App


def test_install_project_targets_managed_python(temp_path, monkeypatch):
    dist = temp_path / "dist"
    dist.mkdir()
    (dist / "project.whl").touch()
    python = temp_path / "managed/bin/python"
    settings = SimpleNamespace(
        app=App(),
        uv=UV(),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=python),
        dirs=SimpleNamespace(app=temp_path, dist=dist, uv=temp_path / "cache"),
    )
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("ivaldi.shared.project.subprocess.run", run)

    install_project(settings)

    python_argument = captured["command"].index("--python") + 1
    assert captured["command"][python_argument] == str(python.resolve())


def test_install_project_uses_manifest_when_dependencies_are_bundled(temp_path, monkeypatch):
    dist = temp_path / "dist"
    dist.mkdir()
    app_wheel = dist / "my_app-1.0-py3-none-any.whl"
    app_wheel.touch()
    (dist / "dependency-2.0-py3-none-any.whl").touch()
    (dist / IVALDI.WHEEL_MANIFEST).write_text(app_wheel.name, encoding="utf-8")
    settings = SimpleNamespace(
        app=App(build={"include_wheels": True}),
        uv=UV(),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=temp_path / "venv/bin/python"),
        dirs=SimpleNamespace(app=temp_path, dist=dist, uv=temp_path / "cache"),
    )
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("ivaldi.shared.project.subprocess.run", run)

    install_project(settings)

    assert str(app_wheel.resolve()) in captured["command"]
    assert "--no-index" in captured["command"]
    assert "dependency-2.0-py3-none-any.whl" not in captured["command"]


def test_install_project_requests_every_wheel_extra(temp_path, monkeypatch):
    dist = temp_path / "dist"
    dist.mkdir()
    app_wheel = dist / "my_app-1.0-py3-none-any.whl"
    with ZipFile(app_wheel, "w") as archive:
        archive.writestr(
            "my_app-1.0.dist-info/METADATA",
            "Metadata-Version: 2.5\nName: my-app\nVersion: 1.0\nProvides-Extra: reports\nProvides-Extra: server\n",
        )
    settings = SimpleNamespace(
        app=App(build={"all_extras": True}),
        uv=UV(),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=temp_path / "venv/bin/python"),
        dirs=SimpleNamespace(app=temp_path, dist=dist, uv=temp_path / "cache"),
    )
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("ivaldi.shared.project.subprocess.run", run)

    install_project(settings)

    assert f"{app_wheel.resolve()}[reports,server]" in captured["command"]


def test_wheel_requirement_rejects_ambiguous_metadata(temp_path):
    wheel = temp_path / "app.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("one.dist-info/METADATA", "Name: one\n")
        archive.writestr("two.dist-info/METADATA", "Name: two\n")
    with pytest.raises(RuntimeError, match="identify metadata"):
        get_wheel_requirement(wheel, all_extras=True)


def test_wheel_requirement_without_extras_is_plain_path(temp_path):
    wheel = temp_path / "app.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("app.dist-info/METADATA", "Metadata-Version: 2.5\nName: app\nVersion: 1\n")
    assert get_wheel_requirement(wheel, all_extras=True) == str(wheel.resolve())


def test_handle_install_flags_includes_every_enabled_option():
    settings = SimpleNamespace(app=App(build={"include_wheels": True}))
    assert handle_install_flags(settings) == ["--no-index"]


@pytest.mark.parametrize("manifest", ["", "../app.whl"])
def test_handle_wheel_rejects_invalid_manifest(temp_path, manifest):
    (temp_path / IVALDI.WHEEL_MANIFEST).write_text(manifest, encoding="utf-8")
    settings = SimpleNamespace(dirs=SimpleNamespace(dist=temp_path))
    with pytest.raises(RuntimeError, match="manifest is invalid"):
        handle_wheel(settings)


def test_handle_wheel_rejects_missing_manifest_wheel(temp_path):
    (temp_path / IVALDI.WHEEL_MANIFEST).write_text("missing.whl", encoding="utf-8")
    settings = SimpleNamespace(dirs=SimpleNamespace(dist=temp_path))
    with pytest.raises(RuntimeError, match="wheel is missing"):
        handle_wheel(settings)


def test_handle_wheel_requires_exactly_one_unmanifested_wheel(temp_path):
    settings = SimpleNamespace(dirs=SimpleNamespace(dist=temp_path))
    with pytest.raises(RuntimeError, match="Could not find"):
        handle_wheel(settings)
    (temp_path / "one.whl").touch()
    (temp_path / "two.whl").touch()
    with pytest.raises(RuntimeError, match="Could not find"):
        handle_wheel(settings)


def test_install_project_reports_nonzero_result(temp_path, monkeypatch):
    (temp_path / "app.whl").touch()
    settings = SimpleNamespace(
        app=App(),
        uv=UV(),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=temp_path / "python"),
        dirs=SimpleNamespace(app=temp_path, dist=temp_path, uv=temp_path / "cache"),
    )
    monkeypatch.setattr("ivaldi.shared.project.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=2))
    with pytest.raises(RuntimeError, match="Project install failed"):
        install_project(settings)


def test_mark_installed_requires_manifest_and_records_wheel(temp_path):
    dist = temp_path / "dist"
    app = temp_path / "app"
    dist.mkdir()
    app.mkdir()
    settings = SimpleNamespace(dirs=SimpleNamespace(dist=dist, app=app))
    with pytest.raises(RuntimeError, match="wheel manifest"):
        mark_installed(settings)

    (dist / IVALDI.WHEEL_MANIFEST).write_text("app.whl", encoding="utf-8")
    mark_installed(settings)
    assert (app / IVALDI.INSTALL_MARKER).read_text(encoding="utf-8") == "app.whl"
