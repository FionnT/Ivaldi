from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

from ivaldi.shared.project import install_project
from ivaldi.types.enums import IVALDI
from ivaldi.types.settings import App


def test_install_project_targets_managed_python(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "project.whl").touch()
    python = tmp_path / "managed/bin/python"
    settings = SimpleNamespace(
        app=App(),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=python),
        dirs=SimpleNamespace(app=tmp_path, dist=dist, uv=tmp_path / "cache"),
    )
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("ivaldi.shared.project.subprocess.run", run)

    install_project(settings)

    python_argument = captured["command"].index("--python") + 1
    assert captured["command"][python_argument] == str(python.resolve())


def test_install_project_uses_manifest_when_dependencies_are_bundled(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    app_wheel = dist / "my_app-1.0-py3-none-any.whl"
    app_wheel.touch()
    (dist / "dependency-2.0-py3-none-any.whl").touch()
    (dist / IVALDI.WHEEL_MANIFEST).write_text(app_wheel.name, encoding="utf-8")
    settings = SimpleNamespace(
        app=App(build={"include_wheels": True}),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=tmp_path / "venv/bin/python"),
        dirs=SimpleNamespace(app=tmp_path, dist=dist, uv=tmp_path / "cache"),
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


def test_install_project_requests_every_wheel_extra(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    app_wheel = dist / "my_app-1.0-py3-none-any.whl"
    with ZipFile(app_wheel, "w") as archive:
        archive.writestr(
            "my_app-1.0.dist-info/METADATA",
            "Metadata-Version: 2.5\nName: my-app\nVersion: 1.0\nProvides-Extra: reports\nProvides-Extra: server\n",
        )
    settings = SimpleNamespace(
        app=App(build={"all_extras": True}),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=tmp_path / "venv/bin/python"),
        dirs=SimpleNamespace(app=tmp_path, dist=dist, uv=tmp_path / "cache"),
    )
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("ivaldi.shared.project.subprocess.run", run)

    install_project(settings)

    assert f"{app_wheel.resolve()}[reports,server]" in captured["command"]
