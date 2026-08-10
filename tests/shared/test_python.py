from pathlib import Path
from types import SimpleNamespace

import pytest

from ivaldi.shared.python import find_python, install_python


def test_install_python_records_managed_interpreter(tmp_path, monkeypatch):
    managed_python = tmp_path / "bin/cpython/bin/python"
    existing_venv = tmp_path / "app/venv"
    existing_venv.mkdir(parents=True)
    stale_file = existing_venv / "stale"
    stale_file.touch()
    monkeypatch.setenv("PYENV_VERSION", "3.14.5")
    monkeypatch.setenv("VIRTUAL_ENV", "/some/active/venv")
    settings = SimpleNamespace(
        bin=SimpleNamespace(uv=Path("/bin/uv"), python=None),
        dirs=SimpleNamespace(app=tmp_path / "app", bin=tmp_path / "bin", uv=tmp_path / "cache"),
        python=SimpleNamespace(version="3.14.5", install_flags=None),
    )
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1:3] == ["python", "find"]:
            return SimpleNamespace(returncode=0, stdout=f"{managed_python}\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("ivaldi.shared.python.subprocess.run", run)

    install_python(settings)

    assert settings.bin.python == settings.dirs.app / "venv/bin/python"
    assert not stale_file.exists()
    assert calls[1][1]["env"]["UV_PYTHON_INSTALL_DIR"] == str(settings.dirs.bin.resolve())
    for _, kwargs in calls:
        assert "PYENV_VERSION" not in kwargs["env"]
        assert "VIRTUAL_ENV" not in kwargs["env"]
        assert kwargs["env"]["UV_MANAGED_PYTHON"] == "1"
    assert calls[2][0][:5] == [
        str(settings.bin.uv.resolve()),
        "venv",
        str((settings.dirs.app / "venv").resolve()),
        "--python",
        str(managed_python.resolve()),
    ]


def make_python_settings(tmp_path):
    return SimpleNamespace(
        bin=SimpleNamespace(uv=tmp_path / "bin/uv", python=None),
        dirs=SimpleNamespace(app=tmp_path / "app", bin=tmp_path / "bin", uv=tmp_path / "cache"),
        python=SimpleNamespace(version="3.14", install_flags=["--default"]),
    )


def test_find_python_rejects_interpreter_outside_install_directory(tmp_path, monkeypatch):
    settings = make_python_settings(tmp_path)
    monkeypatch.setattr(
        "ivaldi.shared.python.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=str(tmp_path / "outside/python")),
    )
    with pytest.raises(RuntimeError, match="outside its managed"):
        find_python(settings)


def test_install_python_reports_install_failure(tmp_path, monkeypatch):
    settings = make_python_settings(tmp_path)
    monkeypatch.setattr(
        "ivaldi.shared.python.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=3),
    )
    with pytest.raises(RuntimeError, match="Python install failed"):
        install_python(settings)


def test_install_python_sets_windows_interpreter_path(tmp_path, monkeypatch):
    settings = make_python_settings(tmp_path)
    managed = settings.dirs.bin / "managed/python.exe"
    monkeypatch.setattr("ivaldi.shared.python.os.name", "nt")
    monkeypatch.setattr("ivaldi.shared.python.find_python", lambda value: managed)
    monkeypatch.setattr(
        "ivaldi.shared.python.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )

    install_python(settings)

    assert settings.bin.python == settings.dirs.app / "venv/Scripts/python.exe"


def test_install_python_reports_venv_failure(tmp_path, monkeypatch):
    settings = make_python_settings(tmp_path)
    managed = settings.dirs.bin / "managed/python"
    results = iter([SimpleNamespace(returncode=0), SimpleNamespace(returncode=4)])
    monkeypatch.setattr("ivaldi.shared.python.find_python", lambda value: managed)
    monkeypatch.setattr("ivaldi.shared.python.subprocess.run", lambda *args, **kwargs: next(results))

    with pytest.raises(RuntimeError, match="Virtual environment creation failed"):
        install_python(settings)
