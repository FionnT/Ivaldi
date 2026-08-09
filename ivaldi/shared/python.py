import logging
import subprocess

logger = logging.getLogger(__name__)


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
    )
    if install.returncode != 0:
        raise RuntimeError(f"Python install failed - exited with code {install.returncode} - {install}")

    logger.info(f"Installed Python {settings.python.version} sucessfully")
