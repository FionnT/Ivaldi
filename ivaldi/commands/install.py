import platform
from pathlib import Path

from ivaldi.shared.admin import claim_root_owned, restore_sudo_ownership
from ivaldi.shared.alias import install_alias
from ivaldi.shared.project import install_project, mark_installed
from ivaldi.shared.python import install_python
from ivaldi.shared.settings import load_install_directories, load_settings
from ivaldi.shared.uv import install_uv
from ivaldi.types.settings import Settings

system = platform.system()


def install(location: Path, executable: Path | None = None) -> Settings:
    settings = load_settings(location=location, build=False)

    try:
        settings = load_install_directories(settings, clean=True)
        install_uv(settings)
        install_python(settings)
        install_project(settings)

        install_alias(settings, executable)
        mark_installed(settings)
    finally:
        app = getattr(settings.dirs, "app", None)  # unset when the platform is unsupported
        if app is not None:
            claim_root_owned(app.parent)
            restore_sudo_ownership(app)
    return settings
