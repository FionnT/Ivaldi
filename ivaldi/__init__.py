import logging
import sys
from pathlib import Path

from ivaldi.commands.build import build as _build
from ivaldi.commands.install import install as _install
from ivaldi.commands.run import run as _run
from ivaldi.shared.admin import is_admin, needs_admin, run_elevated
from ivaldi.shared.settings import is_installed, load_settings

logging.basicConfig(
    force=True,
    level=logging.INFO,
)

location = Path(__file__).parent
usage = "Usage: ivaldi {build,install,run} [args ...]"


def main(args=None):
    arguments = sys.argv[1:] if args is None else args
    if not arguments or arguments[0] in {"-h", "--help"}:
        print(usage)
        return 0

    command, *command_args = arguments
    if command == "run":
        return _run(location, command_args)
    if command_args:
        raise SystemExit(f"{command} does not accept arguments\n{usage}")
    if command == "build":
        _build(location)
        return 0
    if command == "install":
        _install(location)
        return 0
    raise SystemExit(f"Unknown command: {command}\n{usage}")


def build():
    _build(location)


def install():
    _install(location)


def run():
    return _run(location)


def application(args=None, executable=None):
    """Install the bundled application once, then run it with the given arguments."""
    arguments = sys.argv[1:] if args is None else args
    launcher = Path(sys.argv[0] if executable is None else executable).resolve()
    settings = load_settings(location=location, build=False)
    installed = is_installed(settings)
    administrator = is_admin()

    if not installed and needs_admin(settings.platform.admin, "install"):
        if not administrator:
            return run_elevated(launcher, arguments)
        _install(location, executable=launcher)
        if settings.platform.admin == "install":
            return 0
    elif not installed:
        _install(location, executable=launcher)

    if needs_admin(settings.platform.admin, "run") and not administrator:
        return run_elevated(launcher, arguments)
    return _run(location, arguments)
