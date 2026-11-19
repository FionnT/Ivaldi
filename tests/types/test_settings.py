import pytest

from ivaldi.types.settings import App, Platform


def test_app_keeps_configured_entrypoint():
    app = App(
        entrypoint="someproject",
        include=["someproject/**"],
        exclude=["*.pyc"],
        build={"include_wheels": True, "all_extras": True},
        install={"strict": True, "exact": False, "compile_bytecode": False},
    )

    assert app.entrypoint == "someproject"
    assert app.include == ["someproject/**"]
    assert app.exclude == ["*.pyc"]
    assert app.build.include_wheels is True
    assert app.build.all_extras is True
    assert app.install.strict is True
    assert app.install.exact is False
    assert app.install.compile_bytecode is False


@pytest.mark.parametrize(
    ("configured", "expected"),
    [(True, True), (False, False), ("true", True), ("false", False), ("install", "install"), ("run", "run")],
)
def test_platform_normalizes_admin_modes(configured, expected):
    assert Platform(admin=configured).admin == expected


def test_platform_rejects_unknown_admin_mode():
    with pytest.raises(ValueError, match="platform.admin"):
        Platform(admin="sometimes")
