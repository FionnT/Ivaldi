import platform
from pathlib import Path
from types import SimpleNamespace

import pytest

from ivaldi.shared.settings import (
    find_build_file,
    handle_required_settings,
    is_installed,
    load_install_directories,
    load_runtime_directories,
    load_settings,
    parse_settings,
    set_platform_home,
)
from ivaldi.types.enums import IVALDI


def make_settings(location="app"):
    return SimpleNamespace(
        app=SimpleNamespace(entrypoint="package:main"),
        python=SimpleNamespace(version="3.14"),
        platform=SimpleNamespace(location=location, alias="app", add_to_path=True),
        dirs=SimpleNamespace(),
        bin=SimpleNamespace(),
    )


@pytest.mark.parametrize("system", ["Darwin", "Linux", "Windows"])
def test_set_platform_home_for_supported_systems(tmp_path, monkeypatch, system):
    settings = make_settings()
    monkeypatch.setattr("ivaldi.shared.settings.system", system)
    monkeypatch.setattr("ivaldi.shared.settings.Path.home", lambda: tmp_path)
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData/Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData/Local"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    result = set_platform_home(settings)

    assert result is settings
    assert settings.dirs.app.name == "app"
    assert settings.dirs.bin == settings.dirs.app / "bin"
    assert settings.dirs.venv == settings.dirs.app / "venv"
    expected_suffix = ".exe" if system == "Windows" else ""
    assert settings.bin.uv.name == f"uv{expected_suffix}"
    assert settings.bin.python.name == f"python{expected_suffix}"


def test_set_platform_home_rejects_unsupported_system(monkeypatch):
    monkeypatch.setattr("ivaldi.shared.settings.system", "Plan9")
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        set_platform_home(make_settings())


def test_find_build_file_in_start_parent_and_cwd(tmp_path, monkeypatch):
    root = tmp_path / "root"
    nested = root / "one/two"
    nested.mkdir(parents=True)
    config = root / "ivaldi.toml"
    config.touch()
    assert find_build_file(nested) == config

    local_config = nested / "ivaldi.toml"
    local_config.touch()
    monkeypatch.setattr("ivaldi.shared.settings.Path.cwd", lambda: nested)
    assert find_build_file() == local_config


def test_find_build_file_raises_when_absent(tmp_path):
    with pytest.raises(FileNotFoundError, match="Could not find"):
        find_build_file(tmp_path)


def test_handle_required_settings_reports_all_missing_fields():
    settings = make_settings(location=None)
    settings.app.entrypoint = None
    settings.python.version = None
    settings.platform.alias = None
    with pytest.raises(ValueError, match="app.entrypoint.*python.version.*location.*alias"):
        handle_required_settings(settings)


def test_handle_required_settings_accepts_aliasless_no_path_configuration():
    settings = make_settings()
    settings.platform.alias = None
    settings.platform.add_to_path = False
    handle_required_settings(settings)


def test_parse_settings_builds_typed_settings(tmp_path, monkeypatch):
    system = platform.system().lower()
    config = tmp_path / "ivaldi.toml"
    config.write_text(
        "[app]\nentrypoint='package:main'\n"
        "[python]\nversion='3.14'\n"
        f"[{system}]\nlocation='example.app'\nalias='app'\n",
        encoding="utf-8",
    )

    settings = parse_settings(config, tmp_path, tmp_path / "dist", tmp_path / "stage", tmp_path / "output")

    assert settings.app.entrypoint == "package:main"
    assert settings.platform.location == "example.app"
    assert settings.dirs.project == tmp_path


def test_parse_settings_translates_invalid_fields_to_key_error(tmp_path):
    config = tmp_path / "ivaldi.toml"
    config.write_text("[app]\nunknown=true\n", encoding="utf-8")
    with pytest.raises(KeyError, match="unexpected keyword argument"):
        parse_settings(config, tmp_path, tmp_path, tmp_path, tmp_path)


def test_load_settings_configures_build_directories(tmp_path, monkeypatch):
    package = tmp_path / "ivaldi"
    project = tmp_path / "project"
    package.mkdir()
    project.mkdir()
    config = project / "ivaldi.toml"
    config.touch()
    captured = {}
    monkeypatch.setattr("ivaldi.shared.settings.find_build_file", lambda: config)
    monkeypatch.setattr(
        "ivaldi.shared.settings.parse_settings",
        lambda **kwargs: captured.update(kwargs) or "settings",
    )

    assert load_settings(package, build=True) == "settings"
    assert captured["project_folder"] == project
    assert captured["dist"] == package / "dist"
    assert captured["stage"] == package / "stage"
    assert captured["output"] == project / "dist"
    assert captured["dist"].is_dir() and captured["stage"].is_dir()


def test_load_settings_configures_runtime_payload(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "ivaldi.shared.settings.parse_settings",
        lambda **kwargs: captured.update(kwargs) or "settings",
    )

    assert load_settings(tmp_path) == "settings"
    assert captured == {
        "config_file": tmp_path / "dist/ivaldi.toml",
        "project_folder": tmp_path,
        "dist": tmp_path / "dist",
        "stage": None,
        "output": None,
    }


def test_load_install_directories_handles_existing_temporary_and_destination(tmp_path, monkeypatch):
    bundled = tmp_path / "bundle"
    bundled.mkdir()
    (bundled / "new").touch()
    app = tmp_path / "app"
    (app / ".dist.tmp").mkdir(parents=True)
    (app / "dist").mkdir()
    (app / "dist/old").touch()
    settings = make_settings()
    settings.dirs.dist = bundled

    def set_home(value):
        value.dirs.app = app
        value.dirs.exec = tmp_path / "exec"
        value.dirs.bin = app / "bin"
        value.dirs.uv = app / "cache"
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)

    result = load_install_directories(settings)

    assert (result.dirs.dist / "new").is_file()
    assert not (result.dirs.dist / "old").exists()


def test_load_install_directories_rejects_missing_payload(tmp_path, monkeypatch):
    settings = make_settings()
    settings.dirs.dist = tmp_path / "missing"

    def set_home(value):
        value.dirs.app = tmp_path / "app"
        value.dirs.exec = tmp_path / "exec"
        value.dirs.bin = value.dirs.app / "bin"
        value.dirs.uv = value.dirs.app / "cache"
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)
    with pytest.raises(FileNotFoundError, match="payload is missing"):
        load_install_directories(settings)


def test_load_install_directories_accepts_payload_already_in_place(tmp_path, monkeypatch):
    app = tmp_path / "app"
    dist = app / "dist"
    dist.mkdir(parents=True)
    settings = make_settings()
    settings.dirs.dist = dist

    def set_home(value):
        value.dirs.app = app
        value.dirs.exec = tmp_path / "exec"
        value.dirs.bin = app / "bin"
        value.dirs.uv = app / "cache"
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)
    assert load_install_directories(settings).dirs.dist == dist


def test_runtime_directories_and_missing_install_marker(tmp_path, monkeypatch):
    settings = make_settings()

    def set_home(value):
        value.dirs.app = tmp_path
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)
    assert load_runtime_directories(settings) is settings
    assert is_installed(settings) is False


def test_install_marker_is_detected(tmp_path, monkeypatch):
    settings = make_settings()
    (tmp_path / IVALDI.INSTALL_MARKER).touch()
    monkeypatch.setattr("ivaldi.shared.settings.load_runtime_directories", lambda value: set_app(value, tmp_path))
    assert is_installed(settings) is True


def set_app(settings, app):
    settings.dirs.app = app
    return settings
