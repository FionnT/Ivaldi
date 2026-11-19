import shutil
from pathlib import Path

from ivaldi.shared.alias import uninstall_alias
from ivaldi.shared.settings import check_application_location, load_runtime_directories, load_settings
from ivaldi.types.settings import Settings


def uninstall(location: Path) -> Settings:
    """Remove the installed runtime and its command alias."""
    settings = load_settings(location=location, build=False)
    settings = load_runtime_directories(settings)

    check_application_location(settings)

    # Remove the runtime first: if that fails the launcher is still available to retry.
    application_directory = settings.dirs.app
    if application_directory.is_symlink() or application_directory.is_file():
        application_directory.unlink()
    elif application_directory.is_dir():
        shutil.rmtree(application_directory)
    uninstall_alias(settings)
    return settings
