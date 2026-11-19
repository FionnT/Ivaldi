import hashlib
import logging
import platform
import tempfile
import time
from pathlib import Path

import requests

from ivaldi.shared.extract import extract
from ivaldi.types.enums import UV_ARTIFACTS, UV_LINUX_ARTIFACTS, UV_LINUX_MUSL_ARTIFACTS, UV_MACOS_ARTIFACTS, UV_WINDOWS_ARTIFACTS
from ivaldi.types.settings import Settings

logger = logging.getLogger(__name__)


def resolve_release() -> UV_ARTIFACTS:

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


DOWNLOAD_TIMEOUT = (10, 60)
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_PREFIX = ".uv-download-"


def fetch_expected_checksum(url: str) -> str | None:
    """Return the published SHA-256 for a release asset, or None when it is not published."""
    try:
        response = requests.get(url + ".sha256", timeout=DOWNLOAD_TIMEOUT)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        fields = response.text.split()
    except requests.RequestException as error:
        raise RuntimeError(f"Could not fetch the UV checksum from {url}.sha256: {error}") from error
    if not fields or len(fields[0]) != 64:
        raise RuntimeError(f"The UV checksum published at {url}.sha256 is malformed")
    return fields[0].lower()


def download_file(url: str, directory: Path, expected_checksum: str | None) -> Path:
    """Download a URL into a temporary file in ``directory``, verifying size and checksum."""
    temporary = None
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()
            expected_length = response.headers.get("content-length")
            digest = hashlib.sha256()
            written = 0
            with tempfile.NamedTemporaryFile(delete=False, dir=directory, prefix=DOWNLOAD_PREFIX) as f:
                temporary = Path(f.name)
                for data in response.iter_content(chunk_size=64 * 1024):
                    f.write(data)
                    digest.update(data)
                    written += len(data)

        if written == 0:
            raise ValueError(f"Downloaded an empty file from {url}. Please check the URL passed.")
        if expected_length is not None and not response.headers.get("content-encoding") and written != int(expected_length):
            raise OSError(f"Download from {url} was truncated: received {written} of {expected_length} bytes")
        if expected_checksum is not None and digest.hexdigest() != expected_checksum:
            raise ValueError(f"Checksum mismatch for {url}: expected {expected_checksum}, got {digest.hexdigest()}")
        result, temporary = temporary, None
        return result
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, requests.HTTPError):
        return error.response is not None and error.response.status_code >= 500
    return isinstance(error, requests.RequestException | OSError)


def download_with_retries(url: str, directory: Path, expected_checksum: str | None) -> Path:
    """Download ``url``, retrying transient failures with exponential backoff."""
    for attempt in range(1, DOWNLOAD_ATTEMPTS):
        try:
            return download_file(url, directory, expected_checksum)
        except Exception as error:
            if not _is_retryable(error):
                raise
            logger.warning("Download of %s failed (%s); retrying (%d/%d)", url, error, attempt, DOWNLOAD_ATTEMPTS - 1)
            time.sleep(2**attempt)
    return download_file(url, directory, expected_checksum)


def install_uv(settings: Settings):

    repo = settings.uv.repo
    version = settings.uv.version
    release = resolve_release()
    destination = settings.dirs.app / release

    url = repo + "/" + version + "/" + release

    expected_checksum = fetch_expected_checksum(url)
    if expected_checksum is None:
        logger.warning("No published checksum found for %s; skipping integrity verification", url)

    downloaded = download_with_retries(url, settings.dirs.app, expected_checksum)
    downloaded.replace(destination)

    extract(location=destination, destination=settings.dirs.bin)

    executable_suffix = ".exe" if platform.system() == "Windows" else ""
    settings.bin.uv = settings.dirs.bin / f"uv{executable_suffix}"
    settings.bin.uvx = settings.dirs.bin / f"uvx{executable_suffix}"

    missing = [executable for executable in (settings.bin.uv, settings.bin.uvx) if not executable.is_file()]
    if missing:
        names = ", ".join(executable.name for executable in missing)
        raise FileNotFoundError(f"UV archive did not contain the expected executable(s): {names}")

    logger.info("Installed UV %s successfully", version)
