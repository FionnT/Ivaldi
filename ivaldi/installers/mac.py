from ivaldi.shared.project import install_project
from ivaldi.shared.python import install_python
from ivaldi.shared.settings import load_install_directories, user_home
from ivaldi.shared.uv import install_uv


def Install(settings):
    home = user_home()
    app_data = home / "Library" / "Application Support" / settings.platform.location
    exec_dir = (home / "bin").resolve()

    settings = load_install_directories(settings, app_data, exec_dir)

    install_uv(settings)
    install_python(settings)
    install_project(settings)
    return settings
