import tomllib
from pathlib import Path

from ivaldi.settings import UV, UVX, App, Directories, Platform, Poetry, Python, Settings


def find_build_file(start: Path | None = None) -> Path:
    directory = start or Path.cwd()
    candidate = directory / "ivaldi.toml"

    if candidate.is_file():
        return candidate, candidate.parent

    for parent in directory.parents:
        candidate = parent / "ivaldi.toml"
        if candidate.is_file():
            return candidate, candidate.parent

    raise FileNotFoundError(f"Could not find ivaldi.toml in {directory} or any parent directory")


def load_settings(platform):
    file, project_folder = find_build_file()

    with open(file, "rb") as f:
        config = tomllib.load(f)

        try:
            uv = UV(**config.get("uv", {}))
            uvx = UVX(**config.get("uvx", {}))
            poetry = Poetry(**config.get("poetry", {}))
            python = Python(**config.get("python", {}))
            app = App(**config.get("app", {}))
            platform = Platform(**config.get(platform, {}))
            dirs = Directories(project=project_folder)
        except TypeError as err:
            f = str(err).replace(".__init__()", "")
            raise KeyError(f)

        settings = Settings(app=app, python=python, poetry=poetry, uv=uv, uvx=uvx, dirs=dirs, platform=platform)

        return settings


def load_directories(settings: Settings, app_data: Path, exec_dir: Path):
    bin = app_data / "bin"
    uv_cache = app_data / "cache"
    build = app_data / "build"

    app_data.mkdir(exist_ok=True, parents=True)
    bin.mkdir(exist_ok=True, parents=True)
    uv_cache.mkdir(exist_ok=True, parents=True)
    exec_dir.mkdir(exist_ok=True, parents=True)

    settings.dirs.bin = bin
    settings.dirs.uv = uv_cache
    settings.dirs.app = app_data
    settings.dirs.build = build
    settings.exec = exec
    return settings
