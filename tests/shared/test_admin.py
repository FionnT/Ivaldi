import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ivaldi.shared.admin import is_admin, needs_admin, restore_sudo_ownership, run_elevated, sudo_user, user_home


def test_admin_true_applies_to_install_and_run():
    assert needs_admin(True, "install") is True
    assert needs_admin(True, "run") is True


def test_phase_specific_admin_modes():
    assert needs_admin("install", "install") is True
    assert needs_admin("install", "run") is False
    assert needs_admin("run", "install") is False
    assert needs_admin("run", "run") is True
    assert needs_admin(False, "install") is False
    assert needs_admin(False, "run") is False


def test_run_elevated_requests_manual_elevation():
    with pytest.raises(SystemExit, match="sudo|Administrator"):
        run_elevated()


def test_is_admin_uses_effective_user_id(monkeypatch):
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "posix")
    monkeypatch.setattr("ivaldi.shared.admin.os.geteuid", lambda: 0)
    assert is_admin() is True


def test_windows_admin_detection_and_message(monkeypatch):
    ctypes = SimpleNamespace(windll=SimpleNamespace(shell32=SimpleNamespace(IsUserAnAdmin=lambda: 1)))
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "nt")
    monkeypatch.setitem(sys.modules, "ctypes", ctypes)

    assert is_admin() is True
    with pytest.raises(SystemExit, match="Administrator"):
        run_elevated()


def test_sudo_user_uses_original_account(monkeypatch, tmp_path):
    account = SimpleNamespace(pw_dir=str(tmp_path / "home"))
    pwd = SimpleNamespace(getpwuid=lambda uid: account)
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "posix")
    monkeypatch.setattr("ivaldi.shared.admin.os.geteuid", lambda: 0)
    monkeypatch.setenv("SUDO_UID", "1001")
    monkeypatch.setenv("SUDO_GID", "1002")
    monkeypatch.setitem(sys.modules, "pwd", pwd)

    user = sudo_user()
    assert user is not None
    assert (user.uid, user.gid, user.home) == (1001, 1002, tmp_path / "home")
    assert user_home() == tmp_path / "home"


def test_restore_sudo_ownership_repairs_the_complete_tree(monkeypatch, tmp_path):
    app = tmp_path / "app"
    nested = app / "venv"
    nested.mkdir(parents=True)
    executable = nested / "python"
    executable.touch()
    calls = []
    monkeypatch.setattr(
        "ivaldi.shared.admin.sudo_user",
        lambda: SimpleNamespace(uid=1001, gid=1002, home=Path("/home/user")),
    )
    monkeypatch.setattr(
        "ivaldi.shared.admin.os.chown",
        lambda path, uid, gid, follow_symlinks: calls.append((Path(path), uid, gid, follow_symlinks)),
    )

    restore_sudo_ownership(app)

    assert {path for path, *_ in calls} == {app, nested, executable}
    assert all(call[1:] == (1001, 1002, False) for call in calls)


def test_restore_sudo_ownership_is_not_used_on_windows(monkeypatch, tmp_path):
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "nt")
    monkeypatch.setattr(
        "ivaldi.shared.admin.os.chown",
        lambda *_args, **_kwargs: pytest.fail("Windows must retain its native AppData ACLs"),
    )

    restore_sudo_ownership(tmp_path)
