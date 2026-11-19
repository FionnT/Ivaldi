import os
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


@dataclass(frozen=True)
class User:
    uid: int
    gid: int
    home: Path


def sudo_user() -> User | None:
    """Return the user who invoked sudo, when running elevated on POSIX."""
    if os.name == "nt" or os.geteuid() != 0:
        return None

    try:
        uid = int(os.environ["SUDO_UID"])
        gid = int(os.environ["SUDO_GID"])
    except KeyError:
        return None
    except ValueError:
        return None

    if uid <= 0 or gid < 0:
        return None

    import pwd

    try:
        home = Path(pwd.getpwuid(uid).pw_dir)
    except KeyError:
        return None
    return User(uid=uid, gid=gid, home=home)


def user_home() -> Path:
    """Return the invoking user's home, rather than root's home under sudo."""
    user = sudo_user()
    return user.home if user is not None else Path.home()


def restore_sudo_ownership(path: Path) -> None:
    """Return an elevated install tree to the user who invoked sudo.

    Windows elevation retains the user's SID and files created below AppData
    inherit that user's ACL, so no ownership repair is necessary there.
    """
    user = sudo_user()
    if user is None or not path.exists():
        return

    for directory, directories, files in os.walk(path, topdown=False, followlinks=False):
        for name in (*directories, *files):
            os.chown(Path(directory) / name, user.uid, user.gid, follow_symlinks=False)
        os.chown(directory, user.uid, user.gid, follow_symlinks=False)


def claim_root_owned(*paths: Path) -> None:
    """Hand root-owned paths created during an elevated install back to the sudo user.

    Each path and its parents are claimed, stopping before the user's home, so
    directories such as ``~/.local/bin`` and files such as ``~/.zshrc`` that were
    created by root do not stay locked away from the invoking user. Paths owned
    by anyone else, and paths outside the user's home, are left untouched.
    """
    user = sudo_user()
    if user is None:
        return

    for path in paths:
        current = Path(path)
        while current != user.home and current.is_relative_to(user.home):
            try:
                status = current.lstat()
            except FileNotFoundError:
                current = current.parent
                continue
            if status.st_uid == 0:
                os.chown(current, user.uid, user.gid, follow_symlinks=False)
            current = current.parent


def needs_admin(admin: bool | str, phase: str) -> bool:
    """Return whether a configured phase requires administrator privileges."""
    return admin is True or admin == phase


def is_admin() -> bool:
    if os.name == "nt":
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.geteuid() == 0


def run_elevated(*_args: object, **_kwargs: object) -> NoReturn:
    """Stop and ask the user to restart the launcher with elevated privileges."""
    if os.name == "nt":
        raise SystemExit("Administrator privileges are required; rerun this command as Administrator")
    raise SystemExit("Administrator privileges are required; rerun this command with sudo")
