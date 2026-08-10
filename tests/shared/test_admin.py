import pytest

from ivaldi.shared.admin import needs_admin, run_elevated


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
