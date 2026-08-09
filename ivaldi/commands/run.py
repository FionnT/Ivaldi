import subprocess
import sys

from ivaldi.shared.settings import load_runtime_directories, load_settings

ENTRYPOINT_RUNNER = """\
import importlib
import sys

module_name, callable_name, *args = sys.argv[1:]
sys.argv = [module_name, *args]
entrypoint = importlib.import_module(module_name)
for attribute in callable_name.split("."):
    entrypoint = getattr(entrypoint, attribute)
raise SystemExit(entrypoint())
"""


def _entrypoint_command(entrypoint, python, args):
    if ":" not in entrypoint:
        return [entrypoint, *args]

    module_name, callable_name = entrypoint.split(":", 1)
    return [str(python.absolute()), "-c", ENTRYPOINT_RUNNER, module_name, callable_name, *args]


def run(location, args=None):
    settings = load_settings(location=location, build=False)
    settings = load_runtime_directories(settings)
    forwarded_args = sys.argv[1:] if args is None else args

    command = [
        str(settings.bin.uv.resolve()),
        "run",
        "--python",
        str(settings.bin.python.absolute()),
        "--no-python-downloads",
        "--no-config",
        "--cache-dir",
        str(settings.dirs.uv.resolve()),
        "--",
        *_entrypoint_command(settings.app.entrypoint, settings.bin.python, forwarded_args),
    ]
    result = subprocess.run(command, shell=False, check=False, cwd=settings.dirs.app)
    return result.returncode
