import os
import platform
import shlex
import shutil
import stat
import tempfile
from pathlib import Path


def get_shell_config() -> tuple[Path, str]:
    """Return the active shell's startup file and alias syntax."""
    home = Path.home()
    shell = Path(os.environ.get("SHELL", "")).name
    if shell == "zsh":
        return home / ".zshrc", "posix"
    if shell == "bash":
        filename = ".bash_profile" if platform.system() == "Darwin" else ".bashrc"
        return home / filename, "posix"
    if shell == "fish":
        return home / ".config/fish/config.fish", "fish"
    return home / ".profile", "posix"


def write_shell_alias(alias: str, source: Path) -> Path:
    """Create or replace an Ivaldi-managed alias in the shell startup file."""
    config, syntax = get_shell_config()
    quoted_source = shlex.quote(str(source))
    command = f"alias {alias} {quoted_source}" if syntax == "fish" else f"alias {alias}={quoted_source}"
    start_marker = f"# >>> ivaldi alias: {alias} >>>"
    end_marker = f"# <<< ivaldi alias: {alias} <<<"
    block = f"{start_marker}\n{command}\n{end_marker}\n"

    content = config.read_text(encoding="utf-8") if config.is_file() else ""
    start = content.find(start_marker)
    end = content.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start >= 0 and end >= 0:
        end += len(end_marker)
        if end < len(content) and content[end] == "\n":
            end += 1
        content = f"{content[:start]}{block}{content[end:]}"
    else:
        separator = "" if not content or content.endswith("\n") else "\n"
        content = f"{content}{separator}{block}"

    config.parent.mkdir(exist_ok=True, parents=True)
    config.write_text(content, encoding="utf-8")
    return config


def install_command(settings, source: Path, alias: str) -> Path:
    """Copy a launcher into the configured command directory."""
    if platform.system() == "Windows" and not alias.lower().endswith(".exe"):
        alias += ".exe"
    destination = settings.dirs.exec / alias
    if source == destination.resolve():
        return destination

    destination.parent.mkdir(exist_ok=True, parents=True)
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


def install_alias(settings, executable: Path | None) -> Path | None:
    """Persist the configured launcher alias for the current platform."""
    if not settings.platform.add_to_path or executable is None:
        return None

    alias = settings.platform.alias
    if not alias or Path(alias).name != alias:
        raise ValueError("platform.alias must be a command name without path components")

    source = executable.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Could not find the launcher executable: {source}")
    destination = install_command(settings, source, alias)
    if platform.system() == "Windows":
        return destination
    write_shell_alias(alias, destination)
    return destination
