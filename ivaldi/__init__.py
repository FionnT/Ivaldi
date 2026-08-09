import logging
from pathlib import Path

from ivaldi.commands.build import build as _build
from ivaldi.commands.install import install as _install
from ivaldi.commands.run import run as _run

logging.basicConfig(
    force=True,
    level=logging.INFO,
)

location = Path(__file__).parent


def build():
    _build(location)


def install():
    _install(location)


def run():
    _run(location)
