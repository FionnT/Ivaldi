import logging
import os
import sys
from pathlib import Path

from ivaldi.shared.load_settings import load_directories, load_settings

logging.basicConfig(
    force=True,
    level=logging.INFO,
)


def build():

    if sys.platform == "win32":
        from ivaldi.win.installer import Install

        settings = load_settings("win")

        app_data = Path(os.environ["APPDATA"]) / settings.platform.location
        exec_dir = (Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WindowsApps").resolve()
        settings = load_directories(settings, app_data, exec_dir)
    elif sys.platform == "darwin":
        from ivaldi.mac.installer import Install

        settings = load_settings("mac")

        app_data = Path.home() / "Library" / "Application Support" / settings.platform.location
        exec_dir = (Path.home() / "bin").resolve()
        settings = load_directories(settings, app_data, exec_dir)
    elif sys.platform == "linux":
        from ivaldi.linux.installer import Install

        settings = load_settings("linux")

        app_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / settings.platform.location
        exec_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "bin"))
        settings = load_directories(settings, app_data, exec_dir)

    Install(settings)


def run():
    pass
