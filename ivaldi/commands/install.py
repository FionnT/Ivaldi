import platform
from pathlib import Path

from ivaldi.shared.alias import install_alias
from ivaldi.shared.project import mark_installed
from ivaldi.shared.settings import load_settings

system = platform.system()


def install(location, executable: Path | None = None):
    settings = load_settings(location=location, build=False)

    if system == "Darwin":
        from ivaldi.installers.mac import Install
    elif system == "Windows":
        from ivaldi.installers.win import Install
    elif system == "Linux":
        from ivaldi.installers.linux import Install
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

    settings = Install(settings)
    alias = install_alias(settings, executable)
    if not settings.platform.add_to_path or alias is not None:
        mark_installed(settings)
    return settings
