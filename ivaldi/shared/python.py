import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_uv_environment(python_install_dir):
    environment = os.environ.copy()
    for variable in ("CONDA_PREFIX", "PYENV_VERSION", "VIRTUAL_ENV"):
        environment.pop(variable, None)
    environment["UV_PYTHON_INSTALL_DIR"] = str(python_install_dir.resolve())
    environment["UV_MANAGED_PYTHON"] = "1"
    return environment


def find_python(settings):
    uv = f"{settings.bin.uv.resolve()!s}"
    install_dir = settings.dirs.bin.resolve()
    result = subprocess.run(
        [
            uv,
            "python",
            "find",
            settings.python.version,
            "--managed-python",
            "--no-python-downloads",
            "--no-config",
            "--resolve-links",
        ],
        shell=False,
        check=True,
        capture_output=True,
        text=True,
        env=get_uv_environment(install_dir),
    )
    managed_python = Path(result.stdout.strip()).resolve()
    if not managed_python.is_relative_to(install_dir):
        raise RuntimeError(f"uv selected a Python outside its managed install directory: {managed_python}")
    return managed_python


def install_python(settings):

    uv = f"{settings.bin.uv.resolve()!s}"
    dir = f"{settings.dirs.app.resolve()!s}"
    bin = f"{settings.dirs.bin.resolve()!s}"
    uv_cache = f"{settings.dirs.uv.resolve()!s}"

    extra_flags = settings.python.install_flags or []

    flags = ["-q", "--no-config", "--cache-dir", uv_cache, "--no-registry", "--no-bin", "-i", bin] + extra_flags

    command = [uv, "python", "install", settings.python.version, *flags, "--directory", dir]
    install = subprocess.run(
        command,
        shell=False,
        check=True,
        env=get_uv_environment(settings.dirs.bin),
    )
    if install.returncode != 0:
        raise RuntimeError(f"Python install failed - exited with code {install.returncode} - {install}")

    managed_python = find_python(settings)
    settings.dirs.venv = settings.dirs.app / "venv"
    if os.name == "nt":
        settings.bin.python = settings.dirs.venv / "Scripts" / "python.exe"
    else:
        settings.bin.python = settings.dirs.venv / "bin" / "python"

    if settings.dirs.venv.exists():
        shutil.rmtree(settings.dirs.venv)

    create_venv = subprocess.run(
        [
            uv,
            "venv",
            str(settings.dirs.venv.resolve()),
            "--python",
            str(managed_python.resolve()),
            "--managed-python",
            "--no-python-downloads",
            "--no-config",
            "--cache-dir",
            uv_cache,
        ],
        shell=False,
        check=True,
        env=get_uv_environment(settings.dirs.bin),
    )
    if create_venv.returncode != 0:
        raise RuntimeError(f"Virtual environment creation failed - exited with code {create_venv.returncode} - {create_venv}")

    logger.info("Installed Python %s successfully", settings.python.version)
