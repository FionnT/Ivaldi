import os
import platform
import shutil
import tomllib
from pathlib import Path

from ivaldi.types.enums import IVALDI
from ivaldi.types.settings import UV, UVX, App, Directories, Platform, Python, Settings

system = platform.system()


def set_platform_home(settings):

    if system == "Darwin":
        home = Path.home()
        settings.dirs.exec = (home / "bin").resolve()
        settings.dirs.app = home / "Library" / "Application Support" / settings.platform.location
    elif system == "Windows":
        settings.dirs.app = Path(os.environ["APPDATA"]) / settings.platform.location
        settings.dirs.exec = (Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WindowsApps").resolve()

    elif system == "Linux":
        home = Path.home()
        settings.dirs.exec = home / ".local" / "bin"
        settings.dirs.app = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / settings.platform.location
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    settings.dirs.bin = settings.dirs.app / "bin"
    settings.dirs.venv = settings.dirs.app / "venv"
    settings.dirs.uv = settings.dirs.app / "cache"

    if system == "Windows":
        settings.bin.uv = settings.dirs.bin / "uv.exe"
        settings.bin.python = settings.dirs.venv / "Scripts" / "python.exe"
    else:
        settings.bin.uv = settings.dirs.bin / "uv"
        settings.bin.python = settings.dirs.venv / "bin" / "python"

    return settings


def find_build_file(start: Path | None = None) -> tuple[Path, Path]:
    directory = start or Path.cwd()
    candidate = directory / "ivaldi.toml"

    if candidate.is_file():
        return candidate

    for parent in directory.parents:
        candidate = parent / "ivaldi.toml"
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(f"Could not find ivaldi.toml in {directory} or any parent directory")


def handle_required_settings(settings):
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


def parse_settings(config_file: Path, project_folder: Path, dist: Path, stage: Path, output: Path) -> Settings:
    with open(config_file, "rb") as f:
        config = tomllib.load(f)

        try:
            run_platform = config.get(platform.system().lower(), {})

            uv = UV(**config.get("uv", {}))
            uvx = UVX(**config.get("uvx", {}))
            python = Python(**config.get("python", {}))
            app = App(**config.get("app", {}))
            dirs = Directories(project=project_folder, dist=dist, stage=stage, output=output)

            run_platform = Platform(**run_platform)

        except TypeError as err:
            f = str(err).replace(".__init__()", "")
            raise KeyError(f)

        settings = Settings(app=app, python=python, uv=uv, uvx=uvx, dirs=dirs, platform=run_platform)
        handle_required_settings(settings)

        return settings


def load_settings(location: Path, build=False) -> Settings:

    dist = None
    stage = None
    output = None
    project_folder = None

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


def load_install_directories(settings: Settings):
    bundled_dist = settings.dirs.dist.resolve()
    settings = set_platform_home(settings)

    settings.dirs.build = settings.dirs.app / "build"
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


def load_runtime_directories(settings):
    settings = set_platform_home(settings)

    return settings


def is_installed(settings: Settings) -> bool:
    """Return whether the complete runtime needed to launch the app exists."""
    settings = load_runtime_directories(settings)

    marker = settings.dirs.app / IVALDI.INSTALL_MARKER
    return marker.is_file()
