from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


@dataclass
class App:
    def __init__(self, *args: tuple[str], **kwargs: dict[str, str]):
        self.exclude = kwargs.pop("exclude")
        self.include = kwargs.pop("include")

        super().__init__()

    entrypoint: str = None
    include: ClassVar[list[str]] = []
    exclude: ClassVar[list[str]] = [
        "**/__pycache__/**",  # Python cache
        ".venv/**/*",  # Virtual environment
        ".git/**/*",  # Git directory
        "**/tests/**",  # Test files
        "**/*.pyc",  # Compiled Python files
        "**/*.pyo",
        "**/*.pyd",
    ]


@dataclass
class UV:
    def __post_init__(self):
        self.version = self.version.replace("/", "")
        self.repo = self.repo.removesuffix("/")

    location: str = None
    entrypoint: str = None
    version: str = "0.12.3"
    repo: str = "https://releases.astral.sh/github/uv/releases/download/"
    extra_args: list[str] = None


@dataclass
class UVX:
    extra_args: list[str] = None


@dataclass
class Python:
    version: str = None
    gil: bool = True
    install_flags: list[str] = None


@dataclass
class Poetry:
    version: str = None


@dataclass
class Platform:
    name: str = None
    location: str = None
    alias: str = None
    add_to_path: bool = True
    admin: bool = False


@dataclass
class Directories:
    uv: Path = None  # The UV cache directory
    bin: Path = None  # The bin dir that contains the uv and python executables
    app: Path = None  # The location we will store the app in after install
    exec: Path = None  # The location we will store the executable in (e.g. ~/.bin, ~/.local/bin, %APPDATA%/....)
    project: Path = None  # The source project dir
    stage: Path = None  # The staging directory for building
    dist: Path = None  # The dir we ship with the executable, used for installing the program later


@dataclass
class Executables:
    uv: Path = None
    uvx: Path = None
    python: Path = None


@dataclass
class Settings:
    app: App = field(default_factory=App)
    bin: Executables = field(default_factory=Executables)
    dirs: Directories = field(default_factory=Platform)
    platform: Platform = field(default_factory=Platform)
    python: Python = field(default_factory=Python)
    uv: UV = field(default_factory=UV)
    uvx: UVX = field(default_factory=UVX)
