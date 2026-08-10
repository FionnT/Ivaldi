from types import SimpleNamespace

from ivaldi.shared.settings import is_installed, load_install_directories
from ivaldi.types.enums import IVALDI


def test_install_directories_copy_the_bundled_payload(tmp_path):
    bundled = tmp_path / "bundle/dist"
    bundled.mkdir(parents=True)
    (bundled / "ivaldi.toml").write_text("[app]\n", encoding="utf-8")
    (bundled / "project.whl").touch()
    settings = SimpleNamespace(dirs=SimpleNamespace(dist=bundled))

    result = load_install_directories(settings, tmp_path / "app-data", tmp_path / "bin")

    assert result.dirs.dist == tmp_path / "app-data/dist"
    assert (result.dirs.dist / "ivaldi.toml").is_file()
    assert (result.dirs.dist / "project.whl").is_file()


def test_install_state_requires_matching_completed_wheel(tmp_path, monkeypatch):
    dist = tmp_path / "bundle/dist"
    app = tmp_path / "app-data"
    bin_dir = app / "bin"
    python = app / "venv/bin/python"
    dist.mkdir(parents=True)
    bin_dir.mkdir(parents=True)
    python.parent.mkdir(parents=True)
    (dist / IVALDI.WHEEL_MANIFEST).write_text("app-2.whl", encoding="utf-8")
    (app / IVALDI.INSTALL_MARKER).write_text("app-2.whl", encoding="utf-8")
    uv = bin_dir / "uv"
    uv.touch()
    python.touch()
    settings = SimpleNamespace(
        dirs=SimpleNamespace(dist=dist, app=app),
        bin=SimpleNamespace(uv=uv, python=python),
    )
    monkeypatch.setattr("ivaldi.shared.settings.load_runtime_directories", lambda value: value)

    assert is_installed(settings) is True

    (app / IVALDI.INSTALL_MARKER).write_text("app-1.whl", encoding="utf-8")
    assert is_installed(settings) is True
