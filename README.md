# Ivaldi

Ivaldi turns a Python project into a platform-specific, one-file launcher. The launcher embeds the project's wheel and configuration, installs a UV-managed Python environment on its first run, and forwards every later invocation to the installed application.

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

[tool.ivaldi.nuitka]
company-name = "Example Company"
product-name = "My Application"
icon = "./docs/icon.png"

[tool.ivaldi.darwin]
location = "com.example.my-app"
alias = "my-app"
admin = false
```

When no standalone configuration exists, Ivaldi extracts only `[tool.ivaldi]` and writes it to a project-root `ivaldi.toml` before building. Generated files include a schema directive and are refreshed when `[tool.ivaldi]` changes; a hand-written standalone file remains authoritative. The formal configuration definition is available in [`ivaldi.schema.json`](ivaldi.schema.json), and the same schema describes the object nested under `[tool.ivaldi]`.

`include` controls which source files are copied to Ivaldi's clean wheel-build stage. `pyproject.toml` is always included. Add any files referenced by the build configuration, such as a README or license.

`install_args` and `build_args` are passed through to the corresponding UV, UVX, Python, and Nuitka commands. 

Nuitka metadata is passed as `--company-name`, `--product-name`, and `--file-description`. Relative icon paths are resolved from the wrapped project and translated to the platform-specific Nuitka icon option.

`alias` is the installed command name. When `add_to_path` is true, Ivaldi copies the launcher into the platform command directory and, on Unix-like systems, adds an idempotent managed alias pointing to that copy in the active shell's startup file (`.zshrc`, `.bash_profile`, `.bashrc`, Fish's `config.fish`, or `.profile` as applicable). When false, no command alias is installed.

`admin` accepts `true`, `false`, `"install"`, or `"run"`. `true` requires sudo/administrator privileges for both installation and application runs, `"install"` requires them only for first-run installation, `"run"` requires them only for the installed application, and `false` never requires them. Ivaldi does not elevate itself: it stops and asks to be rerun with sudo (or as Administrator on Windows). An `"install"`-only sudo invocation exits after installation so the application can subsequently be run without elevation.

## Build and run

From the wrapped project:

```console
ivaldi build
```

The command builds the project wheel in an isolated environment, places the wheel and `ivaldi.toml` in the embedded payload, optionally collects dependency wheels, and invokes Nuitka. The generated launcher is written to the project's `dist/` directory using the current platform's `alias`. Nuitka uses cached onefile extraction under a cache directory named by the platform's `location` value.

If dependency wheels are requested, Ivaldi uses `uv` from `PATH` when available. Otherwise it downloads the configured UV release into a versioned local tool cache and uses that copy.

On the launcher's first run, Ivaldi downloads UV and the configured Python, creates a dedicated virtual environment in the platform data directory, installs the embedded wheel, and runs the configured entrypoint. Subsequent runs skip installation and forward their arguments through UV to that managed Python environment.
