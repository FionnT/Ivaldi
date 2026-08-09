from pathlib import Path

from ivaldi.shared.python import install_python
from ivaldi.shared.settings import load_directories, load_settings
from ivaldi.shared.uv import install_uv


def Install(location):
    settings = load_settings("location")
    settings = load_directories(settings, app_data, exec_dir)

    app_data = Path.home() / "Library" / "Application Support" / settings.platform.location
    exec_dir = (Path.home() / "bin").resolve()
    install_uv(settings)
    install_python(settings)
