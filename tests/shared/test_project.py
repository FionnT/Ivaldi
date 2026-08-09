from pathlib import Path
from types import SimpleNamespace

from ivaldi.shared.project import install_project
from ivaldi.types.settings import App


def test_install_project_targets_managed_python(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "project.whl").touch()
    python = tmp_path / "managed/bin/python"
    settings = SimpleNamespace(
        app=App(),
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=python),
        dirs=SimpleNamespace(dist=dist, uv=tmp_path / "cache"),
    )
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("ivaldi.shared.project.subprocess.run", run)

    install_project(settings)

    python_argument = captured["command"].index("--python") + 1
    assert captured["command"][python_argument] == str(python.resolve())
