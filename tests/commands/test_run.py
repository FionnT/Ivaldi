from types import SimpleNamespace

from ivaldi.commands.run import entrypoint_command, run
from ivaldi.types.enums import IVALDI


def test_entrypoint_command_uses_executable_entrypoint_without_colon():
    assert entrypoint_command("my-command", None, ["arg"]) == ["my-command", "arg"]


def test_run_uses_installed_python_and_forwards_all_arguments(temp_path, monkeypatch):
    uv = temp_path / "bin/uv"
    python = temp_path / "bin/cpython/bin/python"
    cache = temp_path / "cache"
    app = temp_path / "app"
    settings = SimpleNamespace(
        app=SimpleNamespace(entrypoint="someproject:main"),
        bin=SimpleNamespace(uv=uv, python=python),
        dirs=SimpleNamespace(uv=cache, app=app),
    )
    captured = {}

    monkeypatch.setattr("ivaldi.commands.run.load_settings", lambda **kwargs: settings)
    monkeypatch.setattr("ivaldi.commands.run.load_runtime_directories", lambda value: value)

    def execute(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=23)

    monkeypatch.setattr("ivaldi.commands.run.subprocess.run", execute)

    result = run(temp_path, ["--verbose", "--output", "some file.txt"])

    assert result == 23
    assert captured["kwargs"]["cwd"] == app
    assert captured["command"] == [
        str(uv.resolve()),
        "run",
        "--no-project",
        "--python",
        str(python.resolve()),
        "--no-python-downloads",
        "--no-config",
        "--cache-dir",
        str(cache.resolve()),
        "--",
        str(python.resolve()),
        "-c",
        IVALDI.ENTRYPOINT_RUNNER,
        "someproject",
        "main",
        "--verbose",
        "--output",
        "some file.txt",
    ]
