from types import SimpleNamespace

from ivaldi.shared.collect import collect


def test_specific_include_supersedes_broader_exclude(tmp_path):
    project = tmp_path / "project"
    stage = tmp_path / "stage"
    temp = project / "someproject/storage/temp"
    package = project / "someproject/package"
    temp.mkdir(parents=True)
    package.mkdir(parents=True)

    init_file = temp / "__init__.py"
    excluded_file = temp / "cache.db"
    included_file = package / "module.py"
    pyproject = project / "pyproject.toml"
    for file in (init_file, excluded_file, included_file, pyproject):
        file.touch()

    settings = SimpleNamespace(
        app=SimpleNamespace(
            include=["someproject/**/*", "someproject/storage/temp/**init**.py"],
            exclude=["someproject/storage/temp/*"],
        ),
        dirs=SimpleNamespace(project=project, stage=stage),
    )

    collected = collect(settings)

    assert init_file in collected
    assert excluded_file not in collected
    assert included_file in collected
    assert (stage / "someproject/storage/temp/__init__.py").is_file()
    assert not (stage / "someproject/storage/temp/cache.db").exists()
