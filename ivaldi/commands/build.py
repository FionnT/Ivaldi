import logging
from pathlib import Path

from ivaldi.shared.build import build_all_wheels, build_executable, build_project_wheel, prepare_build
from ivaldi.shared.collect import collect
from ivaldi.shared.settings import load_install_directories, load_settings

logger = logging.getLogger(__name__)


def build(location: Path):
    settings = load_settings(location, build=True)
    settings = load_install_directories(settings)
    prepare_build(settings)
    collect(settings)
    wheel = build_project_wheel(settings)
    if settings.app.build.include_wheels:
        build_all_wheels(settings, wheel)
    return build_executable(location, settings)
