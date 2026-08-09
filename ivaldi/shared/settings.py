import tomllib
from pathlib import Path

from ivaldi.types.settings import UV, UVX, App, Directories, Platform, Python, Settings


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


def load_settings(location: Path, build=False):
    run_platform = None
    dist = None
    stage = None

    if build:
        file, project_folder = find_build_file()
        dist = location / "dist"
        stage = location / "stage"
        dist.mkdir(exist_ok=True, parents=True)
        stage.mkdir(exist_ok=True, parents=True)
        file.copy(dist / file.name)
    else:
        import platform

        project_folder = location
        dist = project_folder / "dist"
        file = dist / "ivaldi.toml"
        run_platform = platform.system().lower()

    with open(file, "rb") as f:
        config = tomllib.load(f)

        try:
            uv = UV(**config.get("uv", {}))
            uvx = UVX(**config.get("uvx", {}))
            python = Python(**config.get("python", {}))
            app = App(**config.get("app", {}))
            dirs = Directories(project=project_folder, dist=dist, stage=stage)

            if run_platform:
                run_platform = Platform(**config.get(run_platform, {}))

        except TypeError as err:
            f = str(err).replace(".__init__()", "")
            raise KeyError(f)

        settings = Settings(app=app, python=python, uv=uv, uvx=uvx, dirs=dirs, platform=run_platform)

        return settings


def load_install_directories(settings: Settings, app_data: Path, exec_dir: Path):
    bin = app_data / "bin"
    uv_cache = app_data / "cache"
    build = app_data / "build"
    dist = app_data / "dist"

    app_data.mkdir(exist_ok=True, parents=True)
    bin.mkdir(exist_ok=True, parents=True)
    uv_cache.mkdir(exist_ok=True, parents=True)
    exec_dir.mkdir(exist_ok=True, parents=True)
    dist.mkdir(exist_ok=True, parents=True)

    settings.dirs.bin = bin
    settings.dirs.uv = uv_cache
    settings.dirs.app = app_data
    settings.dirs.build = build
    settings.exec = exec_dir
    return settings
