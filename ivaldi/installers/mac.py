from pathlib import Path

from ivaldi.shared.project import install_project
from ivaldi.shared.python import install_python
from ivaldi.shared.settings import load_install_directories
from ivaldi.shared.uv import install_uv


def Install(settings):

    app_data = Path.home() / "Library" / "Application Support" / settings.platform.location
    exec_dir = (Path.home() / "bin").resolve()

    settings = load_install_directories(settings, app_data, exec_dir)

    install_uv(settings)
    install_python(settings)
    install_project(settings)
