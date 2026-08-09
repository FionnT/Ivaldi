from pathlib import Path
from types import SimpleNamespace

from ivaldi.shared.python import install_python


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
