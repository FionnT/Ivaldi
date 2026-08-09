from ivaldi.types.settings import App


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
