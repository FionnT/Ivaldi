import logging
import os
import sys
from pathlib import Path

from ivaldi.shared.settings import load_directories, load_settings


def Install(settings):
    settings = load_settings("win")
    app_data = Path(os.environ["APPDATA"]) / settings.platform.location
    exec_dir = (Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WindowsApps").resolve()
    settings = load_directories(settings, app_data, exec_dir)
