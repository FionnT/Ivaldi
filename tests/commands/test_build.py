import platform
import sys
from types import SimpleNamespace

from ivaldi.shared.build import build_all_wheels, build_executable, get_or_build_uv


def test_build_executable_embeds_payload_and_uses_platform_alias(tmp_path, monkeypatch):
    package = tmp_path / "ivaldi"
    payload = package / "dist"
    output = tmp_path / "project/dist"
    package.mkdir()
    payload.mkdir()
    (package / "__main__.py").touch()
    settings = SimpleNamespace(
        dirs=SimpleNamespace(dist=payload, output=output, project=tmp_path / "project"),
        platform=SimpleNamespace(alias="wrapped-app", name="Wrapped App", location="com.example.wrapped-app"),
    )
    captured = {}

    def execute(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs

    monkeypatch.setattr("ivaldi.shared.build.subprocess.run", execute)

    executable = build_executable(package, settings)

    expected_name = "wrapped-app.exe" if platform.system() == "Windows" else "wrapped-app"
    assert executable == output / expected_name
    assert captured["command"][:3] == [sys.executable, "-m", "nuitka"]
    assert f"--include-data-dir={payload.resolve()}=ivaldi/dist" in captured["command"]
    assert f"--output-filename={expected_name}" in captured["command"]
    assert "--onefile-cache-mode=cached" in captured["command"]
    assert "--onefile-tempdir-spec={CACHE_DIR}/com.example.wrapped-app" in captured["command"]
    assert "--python-flag=-m" in captured["command"]
    assert captured["command"][-1] == str(package.resolve())
    assert captured["kwargs"]["cwd"] == tmp_path


def test_build_uv_downloads_configured_release_when_uv_is_not_on_path(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        uv=SimpleNamespace(version="0.12.3"),
        dirs=SimpleNamespace(dist=tmp_path / "ivaldi/dist"),
    )
    settings.dirs.dist.mkdir(parents=True)
    calls = []
    monkeypatch.setattr("ivaldi.shared.build.shutil.which", lambda executable: None)

    def download(local_settings):
        calls.append(local_settings)
        executable = local_settings.dirs.bin / ("uv.exe" if platform.system() == "Windows" else "uv")
        executable.touch()
        local_settings.bin.uv = executable

    monkeypatch.setattr("ivaldi.shared.build.install_uv", download)

    executable = get_or_build_uv(settings)

    assert executable.is_file()
    assert executable.parent == tmp_path / "ivaldi/.tools/0.12.3/bin"
    assert len(calls) == 1


def test_build_all_wheels_uses_uv_tool_run(tmp_path, monkeypatch):
    dist = tmp_path / "ivaldi/dist"
    stage = tmp_path / "ivaldi/stage"
    project = tmp_path / "project"
    for directory in (dist, stage, project):
        directory.mkdir(parents=True)
    wheel = dist / "app-1.0-py3-none-any.whl"
    wheel.touch()
    (stage / "pyproject.toml").write_text("[project]\nname='app'\nversion='1.0'\n", encoding="utf-8")
    uv = tmp_path / "uv"
    uv.touch()
    settings = SimpleNamespace(
        app=SimpleNamespace(build=SimpleNamespace(all_extras=False)),
        uv=SimpleNamespace(extra_args=None),
        uvx=SimpleNamespace(extra_args=None),
        dirs=SimpleNamespace(dist=dist, stage=stage, project=project),
    )
    captured = {}
    monkeypatch.setattr("ivaldi.shared.build.get_or_build_uv", lambda value: uv)
    monkeypatch.setattr(
        "ivaldi.shared.build.subprocess.run",
        lambda command, **kwargs: captured.update(command=command, kwargs=kwargs),
    )

    build_all_wheels(settings, wheel)

    assert captured["command"][:6] == [str(uv.resolve()), "tool", "run", "--from", "pip", "pip"]
