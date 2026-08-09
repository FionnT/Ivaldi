import subprocess
from pathlib import Path

from build import ProjectBuilder
from build.env import DefaultIsolatedEnv

from ivaldi.shared.collect import collect
from ivaldi.shared.settings import load_settings
from ivaldi.types.enums import IVALDI


def build(location: Path):
    settings = load_settings(location, build=True)

    collect(settings)

    # Set up an isolated build environment programmatically
    with DefaultIsolatedEnv() as env:
        builder = ProjectBuilder(settings.dirs.project)

        # Install backend dependencies defined in pyproject.toml [build-system]
        env.install(builder.build_system_requires)

        # Get additional requirements needed for specific outputs
        reqs = builder.get_requires_for_build(
            distribution="wheel",
        )
        env.install(reqs)

        # Run the build using the isolated env runner
        builder.build(distribution="wheel", output_directory=settings.dirs.dist)

        # # Get additional requirements needed for specific outputs
        # reqs = builder.get_requires_for_build(
        #     distribution="sdist",
        # )
        # env.install(reqs)

        # # Run the build using the isolated env runner
        # builder.build(distribution="sdist", output_directory=settings.dirs.dist)


def build_all_wheels(settings):

    # Check for requirements.txt
    wheel_dir = settings.dirs.dist
    project = settings.dirs.build
    req_file = project / "requirements.txt"
    pyproject_file = project / "pyproject.toml"
    uvx = f"{settings.bin.uvx.resolve()!s}"
    project_dir = f"{project.resolve()!s}"

    if req_file.exists() and req_file.is_file():
        cmd = [uvx, "pip", "wheel", "-r", req_file, "--wheel-dir", wheel_dir]
    elif pyproject_file.exists() and pyproject_file.is_file():
        cmd = [uvx, "pip", "wheel", project_dir, "--wheel-dir", wheel_dir]
    else:
        raise FileNotFoundError("No standard Python dependency file found.")

    subprocess.run(cmd, check=True)
