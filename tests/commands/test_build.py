import platform
import sys
from types import SimpleNamespace

import pytest

from ivaldi.shared.build import (
    build_all_wheels,
    build_executable,
    build_project_wheel,
    get_configured_extras,
    get_executable_name,
    get_nuitka_metadata_args,
    get_or_build_uv,
    prepare_build,
)
from ivaldi.types.enums import IVALDI
from ivaldi.types.settings import Nuitka


def test_prepare_build_recreates_stage_and_payload(tmp_path):
    project = tmp_path / "project"
    stage = tmp_path / "stage"
    dist = tmp_path / "dist"
    for directory in (project, stage, dist):
        directory.mkdir()
    (stage / "stale").touch()
    (dist / "stale").touch()
    (project / "ivaldi.toml").write_text("[app]\n", encoding="utf-8")
    settings = SimpleNamespace(dirs=SimpleNamespace(project=project, stage=stage, dist=dist))

    prepare_build(settings)

    assert list(stage.iterdir()) == [stage / ".gitkeep"]
    assert (dist / "ivaldi.toml").read_text(encoding="utf-8") == "[app]\n"


def test_build_project_wheel_uses_isolated_backend_and_writes_manifest(tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    dist = tmp_path / "dist"
    stage.mkdir()
    dist.mkdir()
    installs = []
    builds = []

    class Environment:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def install(self, requirements):
            installs.append(requirements)

    class Builder:
        def __init__(self):
            self.build_system_requires = {"backend"}

        def get_requires_for_build(self, distribution):
            return {"wheel-requirement"}

        def build(self, distribution, output_directory):
            builds.append((distribution, output_directory))
            return str(output_directory / "app.whl")

    monkeypatch.setattr("ivaldi.shared.build.DefaultIsolatedEnv", Environment)
    monkeypatch.setattr("ivaldi.shared.build.ProjectBuilder.from_isolated_env", lambda env, source: Builder())
    settings = SimpleNamespace(dirs=SimpleNamespace(stage=stage, dist=dist))

    wheel = build_project_wheel(settings)

    assert wheel == dist / "app.whl"
    assert installs == [{"backend"}, {"wheel-requirement"}]
    assert builds == [("wheel", dist)]
    assert (dist / IVALDI.WHEEL_MANIFEST).read_text(encoding="utf-8") == "app.whl"


def test_get_configured_extras_reads_optional_dependencies(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "pyproject.toml").write_text(
        "[project.optional-dependencies]\nserver=[]\nreports=[]\n",
        encoding="utf-8",
    )
    settings = SimpleNamespace(app=SimpleNamespace(build=SimpleNamespace(all_extras=True)), dirs=SimpleNamespace(stage=stage))

    assert get_configured_extras(settings) == ["reports", "server"]


def test_get_or_build_uv_prefers_path_and_cached_tool(tmp_path, monkeypatch):
    path_uv = tmp_path / "path-uv"
    monkeypatch.setattr("ivaldi.shared.build.shutil.which", lambda executable: str(path_uv))
    settings = SimpleNamespace(uv=SimpleNamespace(version="1"), dirs=SimpleNamespace(dist=tmp_path / "payload/dist"))
    assert get_or_build_uv(settings) == path_uv

    monkeypatch.setattr("ivaldi.shared.build.shutil.which", lambda executable: None)
    cached = tmp_path / "payload/.tools/1/bin/uv"
    cached.parent.mkdir(parents=True)
    cached.touch()
    assert get_or_build_uv(settings) == cached


def test_build_all_wheels_uses_manifest_extras_and_extra_arguments(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    stage = tmp_path / "stage"
    project = tmp_path / "project"
    for directory in (dist, stage, project):
        directory.mkdir()
    wheel = dist / "app.whl"
    wheel.touch()
    (dist / IVALDI.WHEEL_MANIFEST).write_text(wheel.name, encoding="utf-8")
    (stage / "pyproject.toml").write_text("[project.optional-dependencies]\nb=[]\na=[]\n", encoding="utf-8")
    uv = tmp_path / "uv"
    uv.touch()
    settings = SimpleNamespace(
        app=SimpleNamespace(build=SimpleNamespace(all_extras=True)),
        uv=SimpleNamespace(build_args=["--native-tls"]),
        uvx=SimpleNamespace(build_args=["--isolated"]),
        dirs=SimpleNamespace(dist=dist, stage=stage, project=project),
    )
    captured = {}
    monkeypatch.setattr("ivaldi.shared.build.get_or_build_uv", lambda value: uv)
    monkeypatch.setattr("ivaldi.shared.build.subprocess.run", lambda command, **kwargs: captured.update(command=command))

    build_all_wheels(settings)

    assert "--native-tls" in captured["command"]
    assert "--isolated" in captured["command"]
    assert f"{wheel.resolve()}[a,b]" in captured["command"]


def test_build_all_wheels_requires_manifest(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    settings = SimpleNamespace(dirs=SimpleNamespace(dist=dist))
    monkeypatch.setattr("ivaldi.shared.build.get_or_build_uv", lambda value: tmp_path / "uv")

    with pytest.raises(FileNotFoundError, match="must be built"):
        build_all_wheels(settings)


def test_executable_name_falls_back_and_adds_windows_suffix(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        platform=SimpleNamespace(alias=None, name=None),
        dirs=SimpleNamespace(project=tmp_path / "project"),
    )
    monkeypatch.setattr("ivaldi.shared.build.platform.system", lambda: "Windows")
    assert get_executable_name(settings) == "project.exe"


def test_build_executable_adds_windows_runtime_flag(tmp_path, monkeypatch):
    package = tmp_path / "ivaldi"
    payload = package / "dist"
    output = tmp_path / "output"
    payload.mkdir(parents=True)
    settings = SimpleNamespace(
        dirs=SimpleNamespace(dist=payload, output=output, project=tmp_path / "project"),
        platform=SimpleNamespace(alias="app.exe", name=None, location="app"),
        nuitka=Nuitka(build_args=[]),
    )
    captured = {}
    monkeypatch.setattr("ivaldi.shared.build.platform.system", lambda: "Windows")
    monkeypatch.setattr("ivaldi.shared.build.subprocess.run", lambda command, **kwargs: captured.update(command=command))

    build_executable(package, settings)

    assert "--include-windows-runtime-dlls=yes" in captured["command"]


def test_build_executable_embeds_payload_and_uses_platform_alias(tmp_path, monkeypatch):
    package = tmp_path / "ivaldi"
    payload = package / "dist"
    project = tmp_path / "project"
    output = project / "dist"
    icon = project / "docs/icon.png"
    package.mkdir()
    payload.mkdir()
    icon.parent.mkdir(parents=True)
    icon.touch()
    (package / "__main__.py").touch()
    settings = SimpleNamespace(
        dirs=SimpleNamespace(dist=payload, output=output, project=project),
        platform=SimpleNamespace(alias="wrapped-app", name="Wrapped App", location="com.example.wrapped-app"),
        nuitka=Nuitka(
            build_args=["--clang"],
            company_name="Example Company",
            product_name="Wrapped App",
            file_description="Wrapped application",
            icon="docs/icon.png",
        ),
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
    assert "--clang" in captured["command"]
    assert "--company-name=Example Company" in captured["command"]
    assert "--product-name=Wrapped App" in captured["command"]
    assert "--file-description=Wrapped application" in captured["command"]
    icon_option = {"Darwin": "macos-app-icon", "Windows": "windows-icon-from-ico", "Linux": "linux-icon"}[platform.system()]
    assert f"--{icon_option}={icon.resolve()}" in captured["command"]
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
        uv=SimpleNamespace(build_args=[]),
        uvx=SimpleNamespace(build_args=[]),
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


@pytest.mark.parametrize(
    ("system", "option"),
    [
        ("Darwin", "macos-app-icon"),
        ("Windows", "windows-icon-from-ico"),
        ("Linux", "linux-icon"),
    ],
)
def test_nuitka_metadata_resolves_project_icon(tmp_path, monkeypatch, system, option):
    project = tmp_path / "project"
    icon = project / "docs/icon.png"
    icon.parent.mkdir(parents=True)
    icon.touch()
    settings = SimpleNamespace(
        dirs=SimpleNamespace(project=project),
        nuitka=Nuitka(
            company_name="Neo4j",
            product_name="Neoterm",
            file_description="Support terminal",
            icon="./docs/icon.png",
        ),
    )
    monkeypatch.setattr("ivaldi.shared.build.platform.system", lambda: system)

    arguments = get_nuitka_metadata_args(settings)

    assert "--company-name=Neo4j" in arguments
    assert "--product-name=Neoterm" in arguments
    assert "--file-description=Support terminal" in arguments
    assert f"--{option}={icon.resolve()}" in arguments


def test_nuitka_metadata_rejects_missing_icon(tmp_path):
    settings = SimpleNamespace(
        dirs=SimpleNamespace(project=tmp_path),
        nuitka=Nuitka(icon="missing.png"),
    )
    with pytest.raises(FileNotFoundError, match="configured Nuitka icon"):
        get_nuitka_metadata_args(settings)


def test_nuitka_metadata_rejects_icon_on_unsupported_platform(tmp_path, monkeypatch):
    icon = tmp_path / "icon.png"
    icon.touch()
    settings = SimpleNamespace(dirs=SimpleNamespace(project=tmp_path), nuitka=Nuitka(icon=str(icon)))
    monkeypatch.setattr("ivaldi.shared.build.platform.system", lambda: "Plan9")
    with pytest.raises(RuntimeError, match="not supported"):
        get_nuitka_metadata_args(settings)
