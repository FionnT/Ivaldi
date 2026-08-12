import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path


def extract(location, destination):
    location = Path(location)
    destination = Path(destination)

    destination.mkdir(exist_ok=True, parents=True)

    with tempfile.TemporaryDirectory(dir=location.parent) as temporary:
        extracted = Path(temporary)
        if ".tar" in location.suffixes:
            with tarfile.open(location) as archive:
                archive.extractall(path=extracted, filter="data")
        elif ".zip" in location.suffixes:
            with zipfile.ZipFile(location) as archive:
                archive.extractall(path=extracted)
        else:
            raise ValueError(f"Unsupported archive format: {location}")

        contents = list(extracted.iterdir())
        source = contents[0] if len(contents) == 1 and contents[0].is_dir() else extracted
        for file in source.iterdir():
            if file.is_file():
                shutil.move(file, destination / file.name)

    location.unlink()
