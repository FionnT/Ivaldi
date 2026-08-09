import os
from pathlib import Path

from ivaldi.shared.settings import load_install_directories


def Install(settings):

    app_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / settings.platform.location
    exec_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "bin"))
    settings = load_install_directories(settings, app_data, exec_dir)
