import logging
import sys
from pathlib import Path

from ivaldi.commands.build import build as _build
from ivaldi.commands.install import install as _install
from ivaldi.commands.run import run as _run

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
        return _build(location)
    if command == "install":
        return _install(location)
    raise SystemExit(f"Unknown command: {command}\n{usage}")


def build():
    _build(location)


def install():
    _install(location)


def run():
    return _run(location)
