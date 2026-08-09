import logging
import platform
import tempfile
from os import stat
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

    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        total_length = response.headers.get("content-length")
        if total_length is None:  # no content length header
            raise ValueError(f"Received empty content-length header back from {url}. Please check the URL passed.")
        else:
            try:
                blksize = stat.st_blksize if stat else 4096
            except AttributeError:
                blksize = 4096

            with tempfile.NamedTemporaryFile() as f:
                for data in response.iter_content(chunk_size=blksize):
                    f.write(data)
                Path(f.name).replace(destination)

    extract(location=destination, destination=settings.dirs.bin)

    logger.info(f"Installed UV {version} sucessfully")

    settings.bin.uv = settings.dirs.bin / "uv"
    settings.bin.uvx = settings.dirs.bin / "uvx"
