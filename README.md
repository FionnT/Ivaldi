# Ivaldi

Ivaldi turns a Python project into a platform-specific, one-file launcher. The launcher embeds the project's wheel and configuration, installs a UV-managed Python environment on its first run, and forwards every later invocation to the installed application.

## Configuration

Add `ivaldi.toml` to the project being wrapped:

```toml
[app]
entrypoint = "my_package.cli:main"
include = ["my_package/**/*", "README.md"]

[app.build]
# Bundle dependency wheels for an offline installation.
include_wheels = true
# Build and install every optional dependency group.
all_extras = false

[app.install]
compile_bytecode = true
exact = false
strict = false

[python]
version = "3.14"

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

`include` controls which source files are copied to Ivaldi's clean wheel-build stage. `pyproject.toml` is always included. Add any files referenced by the build configuration, such as a README or license.

`alias` is the installed command name. When `add_to_path` is true, the compiled launcher is copied into the platform command directory under that name; when false, no command alias is installed.

`admin` accepts `true`, `false`, `"install"`, or `"run"`. `true` requires sudo/administrator privileges for both installation and application runs, `"install"` requires them only for first-run installation, `"run"` requires them only for the installed application, and `false` never requires them. Ivaldi does not elevate itself: it stops and asks to be rerun with sudo (or as Administrator on Windows). An `"install"`-only sudo invocation exits after installation so the application can subsequently be run without elevation.

## Build and run

From the wrapped project:

```console
ivaldi build
```

The command builds the project wheel in an isolated environment, places the wheel and `ivaldi.toml` in the embedded payload, optionally collects dependency wheels, and invokes Nuitka. The generated launcher is written to the project's `dist/` directory using the current platform's `alias`. Nuitka uses cached onefile extraction under a cache directory named by the platform's `location` value.

If dependency wheels are requested, Ivaldi uses `uv` from `PATH` when available. Otherwise it downloads the configured UV release into a versioned local tool cache and uses that copy.

On the launcher's first run, Ivaldi downloads UV and the configured Python, creates a dedicated virtual environment in the platform data directory, installs the embedded wheel, and runs the configured entrypoint. Subsequent runs skip installation and forward their arguments through UV to that managed Python environment.
