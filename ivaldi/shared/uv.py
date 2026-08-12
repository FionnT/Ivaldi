import logging
import platform
import tempfile
from pathlib import Path

import requests

from ivaldi.shared.extract import extract
from ivaldi.types.enums import UV_ARTIFACTS, UV_LINUX_ARTIFACTS, UV_LINUX_MUSL_ARTIFACTS, UV_MACOS_ARTIFACTS, UV_WINDOWS_ARTIFACTS
from ivaldi.types.settings import Settings

logger = logging.getLogger(__name__)


def resolve_release():

    system = platform.system()
    machine = platform.machine().upper()

    try:
        if system == "Darwin":
            artifact = UV_MACOS_ARTIFACTS[machine]
        elif system == "Windows":
            artifact = UV_WINDOWS_ARTIFACTS[machine]
        elif system == "Linux":
            if platform.libc_ver()[0].lower() == "musl" or Path("/etc/alpine-release").exists():
                artifact = UV_LINUX_MUSL_ARTIFACTS[machine]
            else:
                artifact = UV_LINUX_ARTIFACTS[machine]
        else:
            raise KeyError
    except KeyError:
        raise RuntimeError(f"UV does not provide an artifact for {system} on {machine}")

    return UV_ARTIFACTS(artifact)


def install_uv(settings: Settings):

    repo = settings.uv.repo
    version = settings.uv.version
    release = resolve_release()
    destination = settings.dirs.app / release

    url = repo + "/" + version + "/" + release

    temporary = None
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            total_length = response.headers.get("content-length")
            if total_length is None:  # no content length header
                raise ValueError(f"Received empty content-length header back from {url}. Please check the URL passed.")

            with tempfile.NamedTemporaryFile(delete=False, dir=settings.dirs.app) as f:
                temporary = Path(f.name)
                for data in response.iter_content(chunk_size=64 * 1024):
                    f.write(data)
            temporary.replace(destination)
            temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    extract(location=destination, destination=settings.dirs.bin)

    executable_suffix = ".exe" if platform.system() == "Windows" else ""
    settings.bin.uv = settings.dirs.bin / f"uv{executable_suffix}"
    settings.bin.uvx = settings.dirs.bin / f"uvx{executable_suffix}"

    missing = [executable for executable in (settings.bin.uv, settings.bin.uvx) if not executable.is_file()]
    if missing:
        names = ", ".join(executable.name for executable in missing)
        raise FileNotFoundError(f"UV archive did not contain the expected executable(s): {names}")

    logger.info("Installed UV %s successfully", version)
