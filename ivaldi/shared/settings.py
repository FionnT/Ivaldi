import json
import logging
import os
import platform
import shutil
import tomllib
from pathlib import Path
from typing import Any

from ivaldi.shared.admin import user_home
from ivaldi.types.enums import IVALDI
from ivaldi.types.settings import UV, UVX, App, Directories, Nuitka, Platform, Python, Settings, require

system = platform.system()
logger = logging.getLogger(__name__)
SCHEMA_URL = "https://raw.githubusercontent.com/FionnT/Ivaldi/main/ivaldi.schema.json"
GENERATED_CONFIG_HEADER = "# Generated from [tool.ivaldi] in pyproject.toml"


def set_platform_home(settings: Settings) -> Settings:
    location = require(settings.platform.location, "platform.location")

    if system == "Darwin":
        home = user_home()
        settings.dirs.exec = home / ".local" / "bin"
        settings.dirs.app = home / "Library" / "Application Support" / location
    elif system == "Windows":
        # Not %LOCALAPPDATA%/<location>: Nuitka extracts the one-file launcher there.
        settings.dirs.app = Path(os.environ["LOCALAPPDATA"]) / "Programs" / location
        settings.dirs.exec = (Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WindowsApps").resolve()
    elif system == "Linux":
        home = user_home()
        settings.dirs.exec = home / ".local" / "bin"

        settings.dirs.app = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / location
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    settings.dirs.bin = settings.dirs.app / "bin"
    settings.dirs.venv = settings.dirs.app / "venv"
    settings.dirs.uv = settings.dirs.app / "cache"

    if system == "Windows":
        settings.bin.uv = settings.dirs.bin / "uv.exe"
        settings.bin.python = settings.dirs.venv / "Scripts" / "python.exe"
        settings.bin.uvx = settings.dirs.bin / "uvx.exe"
    else:
        settings.bin.uv = settings.dirs.bin / "uv"
        settings.bin.uvx = settings.dirs.bin / "uvx"
        settings.bin.python = settings.dirs.venv / "bin" / "python"

    return settings


def format_toml_value(value: object) -> str:
    """Serialize a supported Ivaldi configuration value as TOML."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, list):
        return f"[{', '.join(format_toml_value(item) for item in value)}]"
    raise TypeError(f"Unsupported Ivaldi configuration value: {value!r}")


def format_toml_key(key: str) -> str:
    """Quote TOML keys only when they cannot use bare-key syntax."""
    if key and all(character.isascii() and (character.isalnum() or character in "_-") for character in key):
        return key
    return json.dumps(key, ensure_ascii=False)


def append_toml_table(lines: list[str], path: tuple[str, ...], values: dict[str, Any]) -> None:
    """Append one configuration table and its nested tables."""
    scalar_values = {key: value for key, value in values.items() if not isinstance(value, dict)}
    nested_values = {key: value for key, value in values.items() if isinstance(value, dict)}
    if path:
        lines.append(f"[{'.'.join(format_toml_key(part) for part in path)}]")
    for key, value in scalar_values.items():
        lines.append(f"{format_toml_key(key)} = {format_toml_value(value)}")
    for key, value in nested_values.items():
        if lines and lines[-1] != "":
            lines.append("")
        append_toml_table(lines, (*path, key), value)


def write_ivaldi_config(config: dict[str, Any], destination: Path) -> Path:
    """Write an extracted ``tool.ivaldi`` table as standalone TOML."""
    lines = [f"#:schema {SCHEMA_URL}", GENERATED_CONFIG_HEADER, ""]
    append_toml_table(lines, (), config)
    content = "\n".join(lines).rstrip()
    destination.write_text(f"{content}\n", encoding="utf-8")
    logger.info("Generated %s from pyproject.toml", destination)
    return destination


def extract_pyproject_config(pyproject: Path) -> Path | None:
    """Extract ``tool.ivaldi`` from a pyproject file when configured."""
    if not pyproject.is_file():
        return None
    with open(pyproject, "rb") as file:
        config = tomllib.load(file).get("tool", {}).get("ivaldi")
    if not isinstance(config, dict):
        return None
    return write_ivaldi_config(config, pyproject.parent / "ivaldi.toml")


def find_build_file(start: Path | None = None) -> Path:
    directory = start or Path.cwd()
    for candidate_directory in (directory, *directory.parents):
        candidate = candidate_directory / "ivaldi.toml"
        if candidate.is_file():
            header = candidate.read_text(encoding="utf-8").splitlines()[:2]
            if GENERATED_CONFIG_HEADER in header:
                generated = extract_pyproject_config(candidate_directory / "pyproject.toml")
                if generated is not None:
                    return generated
            return candidate
        generated = extract_pyproject_config(candidate_directory / "pyproject.toml")
        if generated is not None:
            return generated

    raise FileNotFoundError(f"Could not find ivaldi.toml or [tool.ivaldi] in pyproject.toml in {directory} or any parent directory")


def handle_required_settings(settings: Settings):
    missing = []
    if not settings.app.entrypoint:
        missing.append("app.entrypoint")
    if not settings.python.version:
        missing.append("python.version")
    if not settings.platform.location:
        missing.append(f"{platform.system().lower()}.location")
    if settings.platform.add_to_path and not settings.platform.alias:
        missing.append(f"{platform.system().lower()}.alias")
    if missing:
        raise ValueError(f"Missing required Ivaldi setting(s): {', '.join(missing)}")


def parse_settings(config_file: Path, project_folder: Path, dist: Path, stage: Path | None, output: Path | None) -> Settings:
    with open(config_file, "rb") as f:
        config = tomllib.load(f)

        try:
            run_platform = config.get(platform.system().lower(), {})
            uv_config = config.get("uv", {}).copy()
            uvx_config = config.get("uvx", {}).copy()
            nuitka_config = config.get("nuitka", {}).copy()
            for toml_name in ("company-name", "product-name", "file-description"):
                if toml_name in nuitka_config:
                    nuitka_config[toml_name.replace("-", "_")] = nuitka_config.pop(toml_name)

            uv = UV(**uv_config)
            uvx = UVX(**uvx_config)
            python = Python(**config.get("python", {}))
            nuitka = Nuitka(**nuitka_config)
            app = App(**config.get("app", {}))
            dirs = Directories(project=project_folder, dist=dist, stage=stage, output=output)

            run_platform = Platform(**run_platform)

        except TypeError as err:
            f = str(err).replace(".__init__()", "")
            raise KeyError(f)

        settings = Settings(app=app, python=python, uv=uv, uvx=uvx, nuitka=nuitka, dirs=dirs, platform=run_platform)
        handle_required_settings(settings)

        return settings


def load_settings(location: Path, build: bool = False) -> Settings:

    stage: Path | None = None
    output: Path | None = None
    dist: Path
    project_folder: Path

    if build:
        config_file = find_build_file()
        project_folder = config_file.parent
        output = config_file.parent / "dist"
        dist = location / "dist"
        stage = location / "stage"
        dist.mkdir(exist_ok=True, parents=True)
        stage.mkdir(exist_ok=True, parents=True)
    else:
        project_folder = location
        dist = location / "dist"
        config_file = dist / "ivaldi.toml"

    return parse_settings(config_file=config_file, project_folder=project_folder, dist=dist, stage=stage, output=output)


def check_application_location(settings: Settings) -> None:
    """Ensure the configured location is a subdirectory, so removing it cannot touch shared directories."""
    location_path = Path(require(settings.platform.location, "platform.location"))
    if location_path.is_absolute() or location_path == Path(".") or ".." in location_path.parts:
        raise ValueError("platform.location must be a relative application subdirectory")


def remove_previous_install(settings: Settings, bundled_dist: Path) -> None:
    """Delete the entire previous installation, leaving nothing behind."""
    check_application_location(settings)
    application_directory = settings.dirs.app
    if application_directory.is_symlink() or application_directory.is_file():
        application_directory.unlink()
    elif application_directory.is_dir():
        if bundled_dist.is_relative_to(application_directory.resolve()):
            raise RuntimeError(f"Refusing to remove {application_directory}: the bundled installation payload is inside it")
        shutil.rmtree(application_directory)


def load_install_directories(settings: Settings, clean: bool = False) -> Settings:
    bundled_dist = settings.dirs.dist.resolve()
    settings = set_platform_home(settings)
    if clean:
        remove_previous_install(settings, bundled_dist)

    install_dist = settings.dirs.app / "dist"

    settings.dirs.app.mkdir(exist_ok=True, parents=True)
    settings.dirs.exec.mkdir(exist_ok=True, parents=True)
    settings.dirs.bin.mkdir(exist_ok=True, parents=True)
    settings.dirs.uv.mkdir(exist_ok=True, parents=True)

    if bundled_dist != install_dist.resolve():
        if not bundled_dist.is_dir():
            raise FileNotFoundError(f"The bundled installation payload is missing: {bundled_dist}")
        staged_dist = settings.dirs.app / ".dist.tmp"
        if staged_dist.exists():
            shutil.rmtree(staged_dist)
        shutil.copytree(bundled_dist, staged_dist)
        if install_dist.exists():
            shutil.rmtree(install_dist)
        staged_dist.replace(install_dist)
    else:
        install_dist.mkdir(exist_ok=True, parents=True)

    settings.dirs.dist = install_dist

    return settings


def load_runtime_directories(settings: Settings) -> Settings:
    settings = set_platform_home(settings)

    return settings


def is_installed(settings: Settings) -> bool:
    """Return whether the complete runtime needed to launch the app exists."""
    settings = load_runtime_directories(settings)

    marker = settings.dirs.app / IVALDI.INSTALL_MARKER
    return marker.is_file()
