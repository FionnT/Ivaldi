# Ivaldi

Ivaldi turns a Python project into a platform-specific, one-file launcher. The launcher embeds the project's wheel and configuration, installs a UV-managed Python environment on its first run, and forwards every later invocation to the installed application.

[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/FionnT/ivaldi/issues) | [![Code Quality and Tests](https://github.com/FionnT/Ivaldi/actions/workflows/code_quality.yaml/badge.svg)](https://github.com/FionnT/Ivaldi/actions/workflows/code_quality.yaml) [![Coverage badge](https://github.com/FionnT/ivaldi/raw/python-coverage-comment-action-data/badge.svg)](https://github.com/FionnT/ivaldi/tree/python-coverage-comment-action-data)


## Configuration

Add `ivaldi.toml` to the project being wrapped:

```toml
[app]
entrypoint = "my_package.cli:main"
include = ["my_package/**/*", "README.md"]

[uv]
version = "0.12.3"
install_args = []
build_args = []

[uvx]
build_args = []

[python]
version = "3.14.5"
install_args = []

[nuitka]
build_args = []
company-name = "Example Company"
product-name = "My Application"
file-description = "My packaged Python application"
icon = "./docs/icon.png"

[darwin]
name = "My Application"
alias = "my-app"
location = "com.example.my-app"
add_to_path = true
admin = false

[linux]
name = "My Application"
alias = "my-app"
location = "my-app"
add_to_path = true
admin = false

[windows]
name = "My Application"
alias = "my-app"
location = "MyApplication"
add_to_path = true
admin = false
```

The configuration can instead live under `[tool.ivaldi]` in `pyproject.toml`. Prefix each normal section with `tool.ivaldi`, for example:

```toml
[tool.ivaldi.app]
entrypoint = "my_package.cli:main"
include = ["my_package/**/*"]

[tool.ivaldi.python]
version = "3.14.5"

...

```

When no standalone configuration exists, Ivaldi extracts only `[tool.ivaldi]` and writes it to a project-root `ivaldi.toml` before building. Generated files include a schema directive and are refreshed when `[tool.ivaldi]` changes; a hand-written standalone file remains authoritative. The formal configuration definition is available in [`ivaldi.schema.json`](ivaldi.schema.json), and the same schema describes the object nested under `[tool.ivaldi]`.

--- 



## Configuration Flags

All default settings and flags are visible in [the ivaldi settings dataclass](/ivaldi/types/settings.py)


```yaml
[app]
  entrypoint: 
    description: The entrypoint for your application. Can be a module e.g. `mycli` or a specific command, e.g. `mycli:main`
    type: str
    example: mycli:main
  include: 
    description: Controls which source files are copied to Ivaldi's clean wheel-build stage. 
    note: `pyproject.toml` is always included. Add any files referenced by the build configuration, such as a README or license.
    type: list[glob]
    example: ["*.py"]
  exclude: 
    description: Specify files to exclude by a matching pattern. 
    note: If a file would be excluded, but a more specific include would include it, it is superseded by include
    type: list[glob]
    example: ["*.pyc"]
[uv,python]
  version:
    description: Which Python or UVX version to use for your application. 
    No compatability checks are performed, and the wrapped executable does not compile with these versions. 
    `ivaldi build` will use local Python and UV, fetching only UV if required.
  install_args:
    description: Are passed through to the corresponding UV, UVX, Python, and Nuitka commands. 
    note: Overwrites defaults, does not merge them.
    type: list[flag]
    example: ["--compile"]
[uv,uvx,python,nuitka]:
  build_args:
    description: Are passed through to the corresponding UV, UVX, Python, and Nuitka commands. 
    note: Overwrites defaults, does not merge them.
    type: list[flag]
    example: ["--compile",]
[darwin, windows, linux]:
  location: 
    description: The name for a specific subdirectory to install the project to, inside cache directory for that platform (e.g. $HOME/local/.bin)
    type: str
    example: mycli
  add_to_path:
    description: When true, Ivaldi copies the launcher into the platform bin directory (e.g. `~/.local/bin`, `~/.bin`)
    type: bool
  alias: 
    description: In Unix-like systems, adds an idempotent managed alias pointing to that copy.
    note: Attempts to locate the active shell's startup file (`.zshrc`, `.bash_profile`, `.bashrc`, Fish's `config.fish`, or `.profile` as applicable). 
    When false, no command alias is installed. Your command might still be accessible if `add_to_path` was `true`
    type: string
  admin: 
    description: Requires sudo/administrator privileges for installation or application runs.
    note: Ivaldi does not elevate itself. It stops and asks to be rerun with sudo (or as Administrator on Windows). 
    values: 
      - `install` requires sudo only for first-run installation. exits after installation so the application can subsequently be run without elevation.
      - `run` requires sudo only for running the installed application.
      - `true` requires sudo for running and installation.
      - `false` never requires them. 
    type: Literal[true, false, 'install', 'run']
[nuitka]:
  description: Nuitka metadata is passed as `--company-name`, `--product-name`, and `--file-description`. 
  note: Relative icon paths are resolved from the wrapped project and translated to the platform-specific Nuitka icon option.
  name: 
    description: The name to give your executable program
    type: str
    example: mycli
  company: 
    description:
    type: str
    example: My Company
  icon: 
    description: The icon for your program. Will only be visible on Windows, some Linux distro's, and if your application launches a GUI of some kind. 
    type: str(path)
    example: ./static/mycli.png

```
  

## Build and run

From the wrapped project:

```console
ivaldi build
```

The command builds the project wheel in an isolated environment, places the wheel and `ivaldi.toml` in the embedded payload, optionally collects dependency wheels, and invokes Nuitka. The generated launcher is written to the project's `dist/` directory using the current platform's `alias`. Nuitka uses cached onefile extraction under a cache directory named by the platform's `location` value.

If dependency wheels are requested, Ivaldi uses `uv` from `PATH` when available. Otherwise it downloads the configured UV release into a versioned local tool cache and uses that copy.

On the launcher's first run, Ivaldi downloads UV and the configured Python, creates a dedicated virtual environment in the platform data directory, installs the embedded wheel, and runs the configured entrypoint. Subsequent runs skip installation and forward their arguments through UV to that managed Python environment.
