import shutil
from pathlib import Path

from ivaldi.shared.alias import uninstall_alias
from ivaldi.shared.settings import load_runtime_directories, load_settings


def uninstall(location):
    """Remove the installed runtime and its command alias."""
    settings = load_settings(location=location, build=False)
    settings = load_runtime_directories(settings)

    configured_location = settings.platform.location
    location_path = Path(configured_location)
    if location_path.is_absolute() or location_path == Path(".") or ".." in location_path.parts:
        raise ValueError("platform.location must be a relative application subdirectory")

    uninstall_alias(settings)
    application_directory = settings.dirs.app
    if application_directory.is_symlink() or application_directory.is_file():
        application_directory.unlink()
    elif application_directory.is_dir():
        shutil.rmtree(application_directory)
    return settings
