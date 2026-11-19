import json
import platform
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from ivaldi.shared.settings import extract_pyproject_config, find_build_file, format_toml_key, format_toml_value, handle_required_settings, is_installed, load_install_directories, load_runtime_directories, load_settings, parse_settings, set_platform_home
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
def test_set_platform_home_for_supported_systems(temp_path, monkeypatch, system):
    settings = make_settings()
    monkeypatch.setattr("ivaldi.shared.settings.system", system)
    monkeypatch.setattr("ivaldi.shared.settings.Path.home", lambda: temp_path)
    monkeypatch.setenv("APPDATA", str(temp_path / "AppData/Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(temp_path / "AppData/Local"))
    monkeypatch.setenv("XDG_DATA_HOME", str(temp_path / "xdg"))

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


def test_find_build_file_in_start_parent_and_cwd(temp_path, monkeypatch):
    root = temp_path / "root"
    nested = root / "one/two"
    nested.mkdir(parents=True)
    config = root / "ivaldi.toml"
    config.touch()
    assert find_build_file(nested) == config

    local_config = nested / "ivaldi.toml"
    local_config.touch()
    monkeypatch.setattr("ivaldi.shared.settings.Path.cwd", lambda: nested)
    assert find_build_file() == local_config


def test_find_build_file_raises_when_absent(temp_path):
    with pytest.raises(FileNotFoundError, match="Could not find"):
        find_build_file(temp_path)


def test_find_build_file_extracts_tool_ivaldi_from_pyproject(temp_path, caplog):
    project = temp_path / "project"
    nested = project / "src/package"
    nested.mkdir(parents=True)
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        "[project]\nname='unrelated-project'\nversion='1.0'\n"
        "[tool.other]\nenabled=true\n"
        "[tool.ivaldi.app]\nentrypoint='package:main'\ninclude=['package/**']\n"
        "[tool.ivaldi.app.build]\ninclude_wheels=true\n"
        "[tool.ivaldi.python]\nversion='3.14.5'\ninstall_args=[]\n"
        "[tool.ivaldi.nuitka]\ncompany-name='Example'\nicon='icon.png'\n"
        "[tool.ivaldi.darwin]\nlocation='example.app'\nalias='example'\nadmin='install'\n",
        encoding="utf-8",
    )

    generated = find_build_file(nested)

    assert generated == project / "ivaldi.toml"
    with open(generated, "rb") as file:
        config = tomllib.load(file)
    assert config == {
        "app": {
            "entrypoint": "package:main",
            "include": ["package/**"],
            "build": {"include_wheels": True},
        },
        "python": {"version": "3.14.5", "install_args": []},
        "nuitka": {"company-name": "Example", "icon": "icon.png"},
        "darwin": {"location": "example.app", "alias": "example", "admin": "install"},
    }
    assert "project" not in config and "tool" not in config
    assert "Generated" in generated.read_text(encoding="utf-8")
    assert "Generated" in caplog.text


def test_find_build_file_prefers_existing_standalone_config(temp_path):
    standalone = temp_path / "ivaldi.toml"
    standalone.write_text("[app]\nentrypoint='standalone:main'\n", encoding="utf-8")
    (temp_path / "pyproject.toml").write_text(
        "[tool.ivaldi.app]\nentrypoint='embedded:main'\n",
        encoding="utf-8",
    )

    assert find_build_file(temp_path) == standalone
    assert "standalone:main" in standalone.read_text(encoding="utf-8")


def test_find_build_file_refreshes_generated_config(temp_path):
    pyproject = temp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.ivaldi.app]\nentrypoint='first:main'\n",
        encoding="utf-8",
    )
    generated = find_build_file(temp_path)
    assert "first:main" in generated.read_text(encoding="utf-8")

    pyproject.write_text(
        "[tool.ivaldi.app]\nentrypoint='second:main'\n",
        encoding="utf-8",
    )

    assert find_build_file(temp_path) == generated
    content = generated.read_text(encoding="utf-8")
    assert "second:main" in content
    assert "first:main" not in content
    assert content.startswith("#:schema https://")


def test_extract_pyproject_config_ignores_missing_file_and_unconfigured_pyproject(temp_path):
    assert extract_pyproject_config(temp_path / "missing.toml") is None
    pyproject = temp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname='app'\n", encoding="utf-8")
    assert extract_pyproject_config(pyproject) is None


def test_toml_serializer_formats_supported_values_and_quotes_keys():
    assert format_toml_value("value") == '"value"'
    assert format_toml_value(True) == "true"
    assert format_toml_value(3) == "3"
    assert format_toml_value(1.5) == "1.5"
    assert format_toml_value(["one", "two"]) == '["one", "two"]'
    assert format_toml_key("company-name") == "company-name"
    assert format_toml_key("company name") == '"company name"'
    assert format_toml_key("café") == '"café"'
    with pytest.raises(TypeError, match="Unsupported Ivaldi"):
        format_toml_value(object())


def test_ivaldi_schema_defines_standalone_and_tool_table_shape():
    schema_path = Path(__file__).parents[2] / "ivaldi.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["properties"]["nuitka"]["$ref"] == "#/$defs/nuitka"
    assert "The same object may be placed under [tool.ivaldi]" in schema["description"]


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


def test_parse_settings_builds_typed_settings(temp_path, monkeypatch):
    system = platform.system().lower()
    config = temp_path / "ivaldi.toml"
    config.write_text(
        f"[app]\nentrypoint='package:main'\n[python]\nversion='3.14'\n[{system}]\nlocation='example.app'\nalias='app'\n",
        encoding="utf-8",
    )

    settings = parse_settings(config, temp_path, temp_path / "dist", temp_path / "stage", temp_path / "output")

    assert settings.app.entrypoint == "package:main"
    assert settings.platform.location == "example.app"
    assert settings.dirs.project == temp_path


def test_parse_settings_supports_updated_tool_arguments_and_nuitka_metadata(temp_path):
    system = platform.system().lower()
    config = temp_path / "ivaldi.toml"
    config.write_text(
        "[app]\nentrypoint='package:main'\n"
        "[uv]\nversion='0.12.3'\ninstall_args=['--offline']\nbuild_args=['--native-tls']\n"
        "[uvx]\nbuild_args=['--isolated']\n"
        "[python]\nversion='3.14.5'\ninstall_args=['--no-registry']\n"
        "[nuitka]\nbuild_args=['--clang']\ncompany-name='SomeCompany'\nproduct-name='SomeCLI'\n"
        "file-description='SomeCLIProgram'\nicon='./docs/icon.png'\n"
        f"[{system}]\nlocation='SomeCLI'\nalias='SomeCLI'\n",
        encoding="utf-8",
    )

    settings = parse_settings(config, temp_path, temp_path / "dist", temp_path / "stage", temp_path / "output")

    assert settings.uv.install_args == ["--offline"]
    assert settings.uv.build_args == ["--native-tls"]
    assert settings.uvx.build_args == ["--isolated"]
    assert settings.python.install_args == ["--no-registry"]
    assert settings.nuitka.build_args == ["--clang"]
    assert settings.nuitka.company_name == "SomeCompany"
    assert settings.nuitka.product_name == "SomeCLI"
    assert settings.nuitka.file_description == "SomeCLIProgram"
    assert settings.nuitka.icon == "./docs/icon.png"


def test_parse_settings_translates_invalid_fields_to_key_error(temp_path):
    config = temp_path / "ivaldi.toml"
    config.write_text("[app]\nunknown=true\n", encoding="utf-8")
    with pytest.raises(KeyError, match="unexpected keyword argument"):
        parse_settings(config, temp_path, temp_path, temp_path, temp_path)


def test_load_settings_configures_build_directories(temp_path, monkeypatch):
    package = temp_path / "ivaldi"
    project = temp_path / "project"
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


def test_load_settings_configures_runtime_payload(temp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "ivaldi.shared.settings.parse_settings",
        lambda **kwargs: captured.update(kwargs) or "settings",
    )

    assert load_settings(temp_path) == "settings"
    assert captured == {
        "config_file": temp_path / "dist/ivaldi.toml",
        "project_folder": temp_path,
        "dist": temp_path / "dist",
        "stage": None,
        "output": None,
    }


def test_load_install_directories_handles_existing_temporary_and_destination(temp_path, monkeypatch):
    bundled = temp_path / "bundle"
    bundled.mkdir()
    (bundled / "new").touch()
    app = temp_path / "app"
    (app / ".dist.tmp").mkdir(parents=True)
    (app / "dist").mkdir()
    (app / "dist/old").touch()
    settings = make_settings()
    settings.dirs.dist = bundled

    def set_home(value):
        value.dirs.app = app
        value.dirs.exec = temp_path / "exec"
        value.dirs.bin = app / "bin"
        value.dirs.uv = app / "cache"
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)

    result = load_install_directories(settings)

    assert (result.dirs.dist / "new").is_file()
    assert not (result.dirs.dist / "old").exists()


def test_load_install_directories_rejects_missing_payload(temp_path, monkeypatch):
    settings = make_settings()
    settings.dirs.dist = temp_path / "missing"

    def set_home(value):
        value.dirs.app = temp_path / "app"
        value.dirs.exec = temp_path / "exec"
        value.dirs.bin = value.dirs.app / "bin"
        value.dirs.uv = value.dirs.app / "cache"
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)
    with pytest.raises(FileNotFoundError, match="payload is missing"):
        load_install_directories(settings)


def test_load_install_directories_accepts_payload_already_in_place(temp_path, monkeypatch):
    app = temp_path / "app"
    dist = app / "dist"
    dist.mkdir(parents=True)
    settings = make_settings()
    settings.dirs.dist = dist

    def set_home(value):
        value.dirs.app = app
        value.dirs.exec = temp_path / "exec"
        value.dirs.bin = app / "bin"
        value.dirs.uv = app / "cache"
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)
    assert load_install_directories(settings).dirs.dist == dist


def test_runtime_directories_and_missing_install_marker(temp_path, monkeypatch):
    settings = make_settings()

    def set_home(value):
        value.dirs.app = temp_path
        return value

    monkeypatch.setattr("ivaldi.shared.settings.set_platform_home", set_home)
    assert load_runtime_directories(settings) is settings
    assert is_installed(settings) is False


def test_install_marker_is_detected(temp_path, monkeypatch):
    settings = make_settings()
    (temp_path / IVALDI.INSTALL_MARKER).touch()
    monkeypatch.setattr("ivaldi.shared.settings.load_runtime_directories", lambda value: set_app(value, temp_path))
    assert is_installed(settings) is True


def set_app(settings, app):
    settings.dirs.app = app
    return settings
