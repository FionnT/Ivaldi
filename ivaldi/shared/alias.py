import os
import platform
import shutil
import stat
import tempfile
from pathlib import Path


def install_alias(settings, executable: Path | None) -> Path | None:
    """Install the launcher under its configured command alias."""
    if not settings.platform.add_to_path or executable is None:
        return None

    alias = settings.platform.alias
    if not alias or Path(alias).name != alias:
        raise ValueError("platform.alias must be a command name without path components")
    if platform.system() == "Windows" and not alias.lower().endswith(".exe"):
        alias += ".exe"

    source = executable.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Could not find the launcher executable: {source}")
    destination = settings.dirs.exec / alias
    if source == destination.resolve():
        return destination

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent, prefix=f".{alias}.") as file:
            temporary = Path(file.name)
        shutil.copy2(source, temporary)
        if os.name != "nt":
            temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        temporary.replace(destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
