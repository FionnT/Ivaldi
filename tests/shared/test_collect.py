from types import SimpleNamespace

from ivaldi.shared.collect import build_rules, collect, ensure_required_files


def test_ensure_required_files_collects_existing_configuration(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    requirements = project / "requirements.txt"
    readme = project / "README.md"
    requirements.write_text("requests\n", encoding="utf-8")
    readme.write_text("# Existing project\n", encoding="utf-8")

    collected = ensure_required_files([], project)

    assert collected == [requirements, readme]
    assert not (project / "pyproject.toml").exists()


def test_ensure_required_files_prefers_pyproject(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    pyproject = project / "pyproject.toml"
    requirements = project / "requirements.txt"
    pyproject.touch()
    requirements.touch()

    collected = ensure_required_files([], project)

    assert collected == [pyproject]


def test_ensure_required_files_creates_fallback_project_configuration(tmp_path, caplog):
    project = tmp_path / "My Example_App"
    project.mkdir()

    collected = ensure_required_files([], project)

    pyproject = project / "pyproject.toml"
    readme = project / "readme.md"
    assert collected == [pyproject, readme]
    assert 'name = "my-example-app"' in pyproject.read_text(encoding="utf-8")
    assert 'build-backend = "setuptools.build_meta"' in pyproject.read_text(encoding="utf-8")
    assert readme.read_text(encoding="utf-8") == "# My Example_App\n"
    assert "No pyproject.toml or requirements.txt found" in caplog.text


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


def test_build_rules_normalizes_recursive_directory_exclusions(tmp_path):
    settings = SimpleNamespace(
        app=SimpleNamespace(include=[], exclude=["cache/**/*", "build/**"]),
        dirs=SimpleNamespace(project=tmp_path),
    )

    exclusions, includes = build_rules(settings)

    assert exclusions == {"cache/**/*", "cache", "build/**", "build"}
    assert includes == {}
