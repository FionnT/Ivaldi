import platform
from pathlib import Path

from ivaldi.shared.admin import restore_sudo_ownership
from ivaldi.shared.alias import install_alias
from ivaldi.shared.project import install_project, mark_installed
from ivaldi.shared.python import install_python
from ivaldi.shared.settings import load_install_directories, load_settings
from ivaldi.shared.uv import install_uv

system = platform.system()


def install(location, executable: Path | None = None):
    settings = load_settings(location=location, build=False)

    try:
        settings = load_install_directories(settings)
        install_uv(settings)
        install_python(settings)
        install_project(settings)

        alias = install_alias(settings, executable)
        if not settings.platform.add_to_path or alias is not None:
            mark_installed(settings)
    finally:
        if settings.dirs.app is not None:
            restore_sudo_ownership(settings.dirs.app)
    return settings
