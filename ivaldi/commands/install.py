import platform

from ivaldi.shared.settings import load_settings

system = platform.system()


def install(location):
    settings = load_settings(location=location, build=False)

    if system == "Darwin":
        from ivaldi.installers.mac import Install
    elif system == "Windows":
        from ivaldi.installers.win import Install
    elif system == "Linux":
        from ivaldi.installers.linux import Install

    Install(settings)
