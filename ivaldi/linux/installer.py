import os
from pathlib import Path

from ivaldi.shared.settings import load_directories, load_settings


def Install(settings):

    settings = load_settings("linux")
    app_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / settings.platform.location
    exec_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "bin"))
    settings = load_directories(settings, app_data, exec_dir)
