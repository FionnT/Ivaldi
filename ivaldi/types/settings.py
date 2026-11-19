from dataclasses import dataclass, field
from pathlib import Path


def require[T](value: T | None, name: str) -> T:
    """Return a setting that must have been configured by now, or fail with its name."""
    if value is None:
        raise ValueError(f"Missing required Ivaldi setting: {name}")
    return value


@dataclass
class AppBuild:
    include_wheels: bool = False
    all_extras: bool = False


@dataclass
class AppInstall:
    strict: bool = False
    exact: bool = False
    compile_bytecode: bool = True


@dataclass
class App:
    def __post_init__(self):
        if isinstance(self.build, dict):
            self.build = AppBuild(**self.build)  # ty: ignore[invalid-argument-type]
        if isinstance(self.install, dict):
            self.install = AppInstall(**self.install)  # ty: ignore[invalid-argument-type]

    version: str = "0.0.1"
    entrypoint: str | None = None
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(
        default_factory=lambda: [
            "**/__pycache__/**",  # Python cache
            ".venv/**/*",  # Virtual environment
            ".git/**/*",  # Git directory
            "**/tests/**",  # Test files
            "**/*.pyc",  # Compiled Python files
            "**/*.pyo",
            "**/*.pyd",
        ]
    )
    build: AppBuild = field(default_factory=AppBuild)
    install: AppInstall = field(default_factory=AppInstall)


@dataclass
class UV:
    def __post_init__(self):
        self.version = self.version.replace("/", "")
        self.repo = self.repo.removesuffix("/")

    location: str | None = None
    entrypoint: str | None = None
    version: str = "0.12.3"
    repo: str = "https://releases.astral.sh/github/uv/releases/download"
    install_args: list[str] = field(
        default_factory=lambda: [
            "--no-break-system-packages",
            "--no-editable",
            "--reinstall",
            "--no-sources",
            "-q",
            "--no-config",
            "--no-cache",
            "--compile-bytecode",
        ]
    )
    build_args: list[str] = field(default_factory=list)


@dataclass
class UVX:
    build_args: list[str] = field(default_factory=list)


@dataclass
class Python:
    version: str | None = None
    install_args: list[str] = field(
        default_factory=lambda: [
            "--no-registry",
            "-q",
            "--no-config",
            "--no-bin",
        ]
    )


@dataclass
class Poetry:
    version: str | None = None


@dataclass
class Platform:
    def __post_init__(self):
        if isinstance(self.admin, str):
            normalized = self.admin.lower()
            if normalized == "true":
                self.admin = True
            elif normalized == "false":
                self.admin = False
            elif normalized not in {"run", "install"}:
                raise ValueError("platform.admin must be true, false, 'run', or 'install'")

    name: str | None = None
    location: str | None = None
    alias: str | None = None
    add_to_path: bool = True
    admin: bool | str = False


@dataclass
class Directories:
    project: Path  # The source project dir
    dist: Path  # The dir we ship with the executable, used for installing the program later
    stage: Path | None = None  # The staging directory for building (build only)
    output: Path | None = None  # The directory containing the generated wrapper executable (build only)
    # The following are assigned by set_platform_home before they are used.
    uv: Path = field(init=False)  # The UV cache directory
    bin: Path = field(init=False)  # The bin dir that contains the uv and python executables
    app: Path = field(init=False)  # The location we will store the app in after install
    exec: Path = field(init=False)  # The location we will store the executable in (e.g. ~/.local/bin, %LOCALAPPDATA%/Microsoft/WindowsApps)
    venv: Path = field(init=False)  # The application virtual environment


@dataclass
class Nuitka:
    build_args: list[str] = field(
        default_factory=lambda: [
            "--nofollow-import-to=*.tests",
            "--nofollow-import-to=tests",
            "--nofollow-import-to=*.benchmarks",
            "--nofollow-import-to=_decimal",
            "--assume-yes-for-downloads",
            "--remove-output",
            "--no-prefer-source-code",
            "--static-libpython=no",
            "--onefile-no-compression",
        ]
    )
    company_name: str | None = None
    product_name: str | None = None
    file_description: str | None = None
    icon: str | None = None


@dataclass
class Executables:
    # Assigned by set_platform_home (and install_uv/install_python) before they are used.
    uv: Path = field(init=False)
    uvx: Path = field(init=False)
    python: Path = field(init=False)


@dataclass
class Settings:
    dirs: Directories
    app: App = field(default_factory=App)
    bin: Executables = field(default_factory=Executables)
    platform: Platform = field(default_factory=Platform)
    python: Python = field(default_factory=Python)
    uv: UV = field(default_factory=UV)
    uvx: UVX = field(default_factory=UVX)
    nuitka: Nuitka = field(default_factory=Nuitka)
