import subprocess
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

from ivaldi.types.enums import IVALDI


def _wheel_requirement(wheel: Path, all_extras: bool) -> str:
    requirement = str(wheel.resolve())
    if not all_extras:
        return requirement

    with ZipFile(wheel) as archive:
        metadata_files = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1:
            raise RuntimeError(f"Could not identify metadata in the bundled wheel: {wheel.name}")
        metadata = BytesParser().parsebytes(archive.read(metadata_files[0]))
    extras = sorted(metadata.get_all("Provides-Extra", []))
    if extras:
        requirement += f"[{','.join(extras)}]"
    return requirement


def install_project(settings):
    manifest = settings.dirs.dist / IVALDI.WHEEL_MANIFEST
    if manifest.is_file():
        wheel_name = manifest.read_text(encoding="utf-8").strip()
        if not wheel_name or wheel_name != Path(wheel_name).name:
            raise RuntimeError("The bundled wheel manifest is invalid")
        wheel_location = settings.dirs.dist / wheel_name
        if not wheel_location.is_file():
            raise RuntimeError(f"The bundled project wheel is missing: {wheel_name}")
    else:
        wheels = sorted(item for item in settings.dirs.dist.iterdir() if item.is_file() and item.suffix == ".whl")
        wheel_location = wheels[0] if len(wheels) == 1 else None

    if wheel_location is None:
        raise RuntimeError("Could not find the wheel for the program on install! Something went wrong.")

    installed_wheel = wheel_location.name
    wheel_requirement = _wheel_requirement(wheel_location, settings.app.build.all_extras)
    uv = f"{settings.bin.uv.resolve()!s}"
    python = f"{settings.bin.python.absolute()!s}"
    dist = f"{settings.dirs.dist.resolve()!s}"
    uv_cache = f"{settings.dirs.uv.resolve()!s}"

    install_flags = []
    if settings.app.install.compile_bytecode:
        install_flags.append("--compile-bytecode")
    if settings.app.install.exact:
        install_flags.append("--exact")
    if settings.app.install.strict:
        install_flags.append("--strict")
    if settings.app.build.include_wheels:
        install_flags.append("--no-index")

    command = [
        uv,
        "pip",
        "install",
        wheel_requirement,
        "--cache-dir",
        uv_cache,
        "--python",
        python,
        "-q",
        "--no-config",
        "--no-cache",
        *install_flags,
        "--reinstall",
        "--no-sources",
        "--find-links",
        dist,
        "--no-break-system-packages",
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
    return installed_wheel


def mark_installed(settings) -> None:
    manifest = settings.dirs.dist / IVALDI.WHEEL_MANIFEST
    if not manifest.is_file():
        raise RuntimeError("The installed payload does not contain a wheel manifest")
    wheel_name = manifest.read_text(encoding="utf-8").strip()
    (settings.dirs.app / IVALDI.INSTALL_MARKER).write_text(wheel_name, encoding="utf-8")
