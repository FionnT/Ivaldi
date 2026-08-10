import os
import platform
import shutil
import tomllib
from pathlib import Path

from ivaldi.types.settings import UV, UVX, App, Directories, Platform, Python, Settings


def user_home() -> Path:
    if configured_home := os.environ.get("IVALDI_USER_HOME"):
        return Path(configured_home)
    if os.name != "nt" and (sudo_user := os.environ.get("SUDO_USER")) and sudo_user != "root":
        import pwd

        return Path(pwd.getpwnam(sudo_user).pw_dir)
    return Path.home()


def find_build_file(start: Path | None = None) -> tuple[Path, Path]:
    directory = start or Path.cwd()
    candidate = directory / "ivaldi.toml"

    if candidate.is_file():
        return candidate, candidate.parent

    for parent in directory.parents:
        candidate = parent / "ivaldi.toml"
        if candidate.is_file():
            return candidate, candidate.parent

    raise FileNotFoundError(f"Could not find ivaldi.toml in {directory} or any parent directory")


def load_settings(location: Path, build=False):
    run_platform = platform.system().lower()
    dist = None
    stage = None

    if build:
        file, project_folder = find_build_file()
        dist = location / "dist"
        stage = location / "stage"
        output = project_folder / "dist"
        dist.mkdir(exist_ok=True, parents=True)
        stage.mkdir(exist_ok=True, parents=True)
    else:
        project_folder = location
        dist = project_folder / "dist"
        output = None
        file = dist / "ivaldi.toml"

    with open(file, "rb") as f:
        config = tomllib.load(f)

        try:
            uv = UV(**config.get("uv", {}))
            uvx = UVX(**config.get("uvx", {}))
            python = Python(**config.get("python", {}))
            app = App(**config.get("app", {}))
            dirs = Directories(project=project_folder, dist=dist, stage=stage, output=output)

            run_platform = Platform(**config.get(run_platform, {}))

        except TypeError as err:
            f = str(err).replace(".__init__()", "")
            raise KeyError(f)

        settings = Settings(app=app, python=python, uv=uv, uvx=uvx, dirs=dirs, platform=run_platform)

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

        return settings


def load_install_directories(settings: Settings, app_data: Path, exec_dir: Path):
    bundled_dist = settings.dirs.dist.resolve()
    bin = app_data / "bin"
    uv_cache = app_data / "cache"
    build = app_data / "build"
    dist = app_data / "dist"

    app_data.mkdir(exist_ok=True, parents=True)
    bin.mkdir(exist_ok=True, parents=True)
    uv_cache.mkdir(exist_ok=True, parents=True)
    exec_dir.mkdir(exist_ok=True, parents=True)
    if bundled_dist != dist.resolve():
        if not bundled_dist.is_dir():
            raise FileNotFoundError(f"The bundled installation payload is missing: {bundled_dist}")
        staged_dist = app_data / ".dist.tmp"
        if staged_dist.exists():
            shutil.rmtree(staged_dist)
        shutil.copytree(bundled_dist, staged_dist)
        if dist.exists():
            shutil.rmtree(dist)
        staged_dist.replace(dist)
    else:
        dist.mkdir(exist_ok=True, parents=True)

    settings.dirs.bin = bin
    settings.dirs.uv = uv_cache
    settings.dirs.app = app_data
    settings.dirs.build = build
    settings.dirs.dist = dist
    settings.dirs.exec = exec_dir
    return settings


def load_runtime_directories(settings):
    system = platform.system()
    home = user_home()

    if system == "Darwin":
        app_data = home / "Library" / "Application Support" / settings.platform.location
    elif system == "Windows":
        app_data = Path(os.environ["APPDATA"]) / settings.platform.location
    elif system == "Linux":
        app_data = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / settings.platform.location
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    settings.dirs.app = app_data
    settings.dirs.bin = app_data / "bin"
    settings.dirs.uv = app_data / "cache"
    settings.dirs.venv = app_data / "venv"
    settings.bin.uv = settings.dirs.bin / ("uv.exe" if system == "Windows" else "uv")
    if system == "Windows":
        settings.bin.python = settings.dirs.venv / "Scripts" / "python.exe"
    else:
        settings.bin.python = settings.dirs.venv / "bin" / "python"
    return settings


def is_installed(settings: Settings) -> bool:
    """Return whether the complete runtime needed to launch the app exists."""
    from ivaldi.types.enums import IVALDI

    settings = load_runtime_directories(settings)
    marker = settings.dirs.app / IVALDI.INSTALL_MARKER
    return marker.is_file()
