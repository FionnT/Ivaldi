import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ivaldi.shared.admin import claim_root_owned, is_admin, needs_admin, restore_sudo_ownership, run_elevated, sudo_user, user_home


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


def test_sudo_user_uses_original_account(monkeypatch, temp_path):
    account = SimpleNamespace(pw_dir=str(temp_path / "home"))
    pwd = SimpleNamespace(getpwuid=lambda uid: account)
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "posix")
    monkeypatch.setattr("ivaldi.shared.admin.os.geteuid", lambda: 0)
    monkeypatch.setenv("SUDO_UID", "1001")
    monkeypatch.setenv("SUDO_GID", "1002")
    monkeypatch.setitem(sys.modules, "pwd", pwd)

    user = sudo_user()
    assert user is not None
    assert (user.uid, user.gid, user.home) == (1001, 1002, temp_path / "home")
    assert user_home() == temp_path / "home"


def test_sudo_user_requires_sudo_environment(monkeypatch):
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "posix")
    monkeypatch.setattr("ivaldi.shared.admin.os.geteuid", lambda: 0)
    monkeypatch.delenv("SUDO_UID", raising=False)
    monkeypatch.delenv("SUDO_GID", raising=False)

    assert sudo_user() is None


@pytest.mark.parametrize(
    ("uid", "gid"),
    [("invalid", "1002"), ("1001", "invalid"), ("0", "1002"), ("1001", "-1")],
)
def test_sudo_user_rejects_invalid_ids(monkeypatch, uid, gid):
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "posix")
    monkeypatch.setattr("ivaldi.shared.admin.os.geteuid", lambda: 0)
    monkeypatch.setenv("SUDO_UID", uid)
    monkeypatch.setenv("SUDO_GID", gid)

    assert sudo_user() is None


def test_sudo_user_rejects_an_unknown_account(monkeypatch):
    def unknown_user(_uid):
        raise KeyError

    monkeypatch.setattr("ivaldi.shared.admin.os.name", "posix")
    monkeypatch.setattr("ivaldi.shared.admin.os.geteuid", lambda: 0)
    monkeypatch.setenv("SUDO_UID", "1001")
    monkeypatch.setenv("SUDO_GID", "1002")
    monkeypatch.setitem(sys.modules, "pwd", SimpleNamespace(getpwuid=unknown_user))

    assert sudo_user() is None


def test_restore_sudo_ownership_repairs_the_complete_tree(monkeypatch, temp_path):
    app = temp_path / "app"
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


def test_restore_sudo_ownership_is_not_used_on_windows(monkeypatch, temp_path):
    monkeypatch.setattr("ivaldi.shared.admin.os.name", "nt")
    monkeypatch.setattr(
        "ivaldi.shared.admin.os.chown",
        lambda *_args, **_kwargs: pytest.fail("Windows must retain its native AppData ACLs"),
    )

    restore_sudo_ownership(temp_path)


def test_claim_root_owned_chowns_only_root_owned_paths_below_home(monkeypatch, temp_path):
    home = temp_path / "home"
    nested = home / ".local" / "bin"
    nested.mkdir(parents=True)
    launcher = nested / "tool"
    launcher.touch()
    calls = []
    monkeypatch.setattr("ivaldi.shared.admin.sudo_user", lambda: SimpleNamespace(uid=1001, gid=1002, home=home))
    monkeypatch.setattr("ivaldi.shared.admin.os.chown", lambda path, uid, gid, follow_symlinks: calls.append(Path(path)))

    class Status:
        def __init__(self, uid):
            self.st_uid = uid

    owners = {launcher: 0, nested: 0, nested.parent: 1001}
    monkeypatch.setattr(Path, "lstat", lambda self: Status(owners.get(self, 0)))

    claim_root_owned(launcher, temp_path / "outside")

    assert calls == [launcher, nested]


def test_claim_root_owned_is_a_no_op_without_sudo(monkeypatch, temp_path):
    monkeypatch.setattr("ivaldi.shared.admin.sudo_user", lambda: None)
    monkeypatch.setattr("ivaldi.shared.admin.os.chown", lambda *_a, **_k: pytest.fail("must not chown"))
    claim_root_owned(temp_path)
