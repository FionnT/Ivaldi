import os


def needs_admin(admin: bool | str, phase: str) -> bool:
    """Return whether a configured phase requires administrator privileges."""
    return admin is True or admin == phase


def is_admin() -> bool:
    if os.name == "nt":
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.geteuid() == 0


def run_elevated(*_args, **_kwargs):
    """Stop and ask the user to restart the launcher with elevated privileges."""
    if os.name == "nt":
        raise SystemExit("Administrator privileges are required; rerun this command as Administrator")
    raise SystemExit("Administrator privileges are required; rerun this command with sudo")
