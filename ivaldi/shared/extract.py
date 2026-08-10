import shutil
import tarfile
import zipfile
from pathlib import Path


def extract(location, destination):
    location = Path(location)
    destination = Path(destination)

    destination.mkdir(exist_ok=True, parents=True)

    if ".tar" in location.suffixes:
        with tarfile.open(location) as archive:
            archive.extractall(path=str(location.parent), filter="data")
    elif ".zip" in location.suffixes:
        with zipfile.ZipFile(location) as archive:
            archive.extractall(path=str(location.parent))
    else:
        raise ValueError(f"Unsupported archive format: {location}")

    location.unlink()
    for f in location.parent.iterdir():
        if f.is_dir() and f.name in location.name:
            for subf in f.iterdir():
                if subf.is_file():
                    shutil.move(subf, destination / subf.name)
            shutil.rmtree(f)
