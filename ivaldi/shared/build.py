import logging
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

from build import ProjectBuilder
from build.env import DefaultIsolatedEnv

from ivaldi.shared.uv import install_uv
from ivaldi.types.enums import IVALDI

logger = logging.getLogger(__name__)


def prepare_build(settings):
    """Create clean source and payload directories for a reproducible build."""
    for directory in (settings.dirs.stage, settings.dirs.dist):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)
    (settings.dirs.stage / ".gitkeep").touch()

    config = settings.dirs.project / "ivaldi.toml"
    shutil.copy2(config, settings.dirs.dist / config.name)


def build_project_wheel(settings) -> Path:
    with DefaultIsolatedEnv() as env:
        builder = ProjectBuilder.from_isolated_env(env, settings.dirs.stage)
        env.install(builder.build_system_requires)
        env.install(builder.get_requires_for_build(distribution="wheel"))
        wheel = builder.build(distribution="wheel", output_directory=settings.dirs.dist)

    wheel = Path(wheel)
    (settings.dirs.dist / IVALDI.WHEEL_MANIFEST).write_text(wheel.name, encoding="utf-8")
    return wheel


def get_configured_extras(settings) -> list[str]:
    if not settings.app.build.all_extras:
        return []
    with open(settings.dirs.stage / "pyproject.toml", "rb") as file:
        project = tomllib.load(file).get("project", {})
    return sorted(project.get("optional-dependencies", {}))


def get_or_build_uv(settings) -> Path:
    available_uv = shutil.which("uv")
    if available_uv:
        return Path(available_uv)

    tools = settings.dirs.dist.parent / ".tools" / settings.uv.version
    executable = tools / "bin" / ("uv.exe" if platform.system() == "Windows" else "uv")
    if executable.is_file():
        return executable

    local_settings = SimpleNamespace(
        uv=settings.uv,
        dirs=SimpleNamespace(app=tools, bin=tools / "bin"),
        bin=SimpleNamespace(uv=None, uvx=None),
    )
    local_settings.dirs.bin.mkdir(parents=True, exist_ok=True)
    install_uv(local_settings)
    return local_settings.bin.uv


def build_all_wheels(settings, wheel_location: Path | None = None):
    """Download wheels for every runtime dependency into the embedded payload."""
    uv = get_or_build_uv(settings)

    if wheel_location is None:
        manifest = settings.dirs.dist / IVALDI.WHEEL_MANIFEST
        if not manifest.is_file():
            raise FileNotFoundError("The application wheel must be built before its dependencies")
        wheel_location = settings.dirs.dist / manifest.read_text(encoding="utf-8").strip()

    extras = get_configured_extras(settings)
    requirement = str(wheel_location.resolve())
    if extras:
        requirement += f"[{','.join(extras)}]"

    command = [
        str(uv.resolve()),
        *(settings.uv.build_args or []),
        "tool",
        "run",
        *(settings.uvx.build_args or []),
        "--from",
        "pip",
        "pip",
        "wheel",
        requirement,
        "--wheel-dir",
        str(settings.dirs.dist.resolve()),
    ]
    subprocess.run(command, shell=False, check=True, cwd=settings.dirs.project)


def get_executable_name(settings) -> str:
    name = settings.platform.alias or settings.platform.name or settings.dirs.project.name
    if platform.system() == "Windows" and not name.lower().endswith(".exe"):
        name += ".exe"
    return name


def get_nuitka_metadata_args(settings) -> list[str]:
    """Build Nuitka metadata and platform-specific icon arguments."""
    arguments = []
    for option, value in (
        ("company-name", settings.nuitka.company_name),
        ("product-name", settings.nuitka.product_name),
        ("file-description", settings.nuitka.file_description),
    ):
        if value:
            arguments.append(f"--{option}={value}")

    if settings.nuitka.icon:
        icon = Path(settings.nuitka.icon)
        if not icon.is_absolute():
            icon = settings.dirs.project / icon
        icon = icon.resolve()
        if not icon.is_file():
            raise FileNotFoundError(f"Could not find the configured Nuitka icon: {icon}")
        icon_option = {
            "Darwin": "macos-app-icon",
            "Windows": "windows-icon-from-ico",
            "Linux": "linux-icon",
        }.get(platform.system())
        if icon_option is None:
            raise RuntimeError(f"Nuitka icons are not supported on {platform.system()}")
        arguments.append(f"--{icon_option}={icon}")

    return arguments


def build_executable(location: Path, settings) -> Path:
    """Compile Ivaldi as a one-file wrapper containing the installation payload."""
    output_dir = settings.dirs.output
    output_dir.mkdir(exist_ok=True, parents=True)
    output_name = get_executable_name(settings)

    command = [
        sys.executable,
        "-m",
        "nuitka",
        f"--output-dir={output_dir.resolve()}",
        f"--output-filename={output_name}",
        f"--include-data-dir={settings.dirs.dist.resolve()}=ivaldi/dist",
        f"--onefile-tempdir-spec={{CACHE_DIR}}/{settings.platform.location}",
        "--onefile-cache-mode=cached",
        "--mode=onefile",
        "--python-flag=-m",
        *(settings.nuitka.build_args or []),
        *get_nuitka_metadata_args(settings),
        str(location.resolve()),
    ]

    logger.info(f"Running Nuitka build with: command {command!s}")
    if platform.system() == "Windows":
        command.insert(-1, "--include-windows-runtime-dlls=yes")

    subprocess.run(command, shell=False, check=True, cwd=location.parent)
    return output_dir / output_name
