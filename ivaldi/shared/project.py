import subprocess


def install_project(settings):

    wheel_location = None
    for item in settings.dirs.dist.iterdir():
        if item.is_file() and item.suffix == ".whl":
            wheel_location = item
    if not wheel_location:
        raise RuntimeError("Could not find the wheel for the program on install! Something went wrong.")

    wheel_location = f"{wheel_location.resolve()!s}"
    uv = f"{settings.bin.uv.resolve()!s}"
    dist = f"{settings.dirs.dist.resolve()!s}"
    uv_cache = f"{settings.dirs.uv.resolve()!s}"

    command = [
        uv,
        "pip",
        "install",
        "wheel",
        wheel_location,
        "--cache-dir",
        uv_cache,
        "--managed-python",
        "-q",
        "--no-config",
        "--no-cache",
        "--compile-bytecode",
        "--reinstall",
        "--no-sources",
        "--find-links",
        dist,
        "--exact",
        "--strict",
        "--no-break-system-packages",
        # "--all-extras",
        "--no-editable",
        "--directory",
        dist,
    ]

    install = subprocess.run(
        command,
        shell=False,
        check=True,
    )
    if install.returncode != 0:
        raise RuntimeError(f"Project install failed - exited with code {install.returncode} - {install}")
