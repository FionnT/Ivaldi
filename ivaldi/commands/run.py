import subprocess
import sys

from ivaldi.shared.settings import load_runtime_directories, load_settings
from ivaldi.types.enums import IVALDI


def entrypoint_command(entrypoint, python, args):
    if ":" not in entrypoint:
        return [entrypoint, *args]

    module_name, callable_name = entrypoint.split(":", 1)
    return [str(python.absolute()), "-c", IVALDI.ENTRYPOINT_RUNNER, module_name, callable_name, *args]


def run(location, args=None):
    settings = load_settings(location=location, build=False)
    settings = load_runtime_directories(settings)
    forwarded_args = sys.argv[1:] if args is None else args

    command = [
        str(settings.bin.uv.resolve()),
        "run",
        "--no-project",
        "--python",
        str(settings.bin.python.absolute()),
        "--no-python-downloads",
        "--no-config",
        "--cache-dir",
        str(settings.dirs.uv.resolve()),
        "--",
        *entrypoint_command(settings.app.entrypoint, settings.bin.python, forwarded_args),
    ]
    result = subprocess.run(command, shell=False, check=False, cwd=settings.dirs.app)
    return result.returncode
