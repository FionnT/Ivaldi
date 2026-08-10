import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _rule_specificity(rule):
    """Rank path rules by how narrowly they describe a path."""
    literal_characters = sum(character not in "*?[]" for character in rule)
    wildcard_characters = sum(character in "*?[]" for character in rule)
    return literal_characters, -wildcard_characters, len(rule)


def build_rules(settings):
    exclusion_rules = set()
    for rule in settings.app.exclude:
        rule = rule.rstrip("/")
        exclusion_rules.add(rule)
        if rule.endswith("/**/*"):
            exclusion_rules.add(rule[:-5])
        elif rule.endswith("/**"):
            exclusion_rules.add(rule[:-3])

    include_rules_by_item = {}
    for rule in settings.app.include:
        for item in settings.dirs.project.glob(rule):
            include_rules_by_item.setdefault(item, []).append(rule)

    return exclusion_rules, include_rules_by_item


def collect_files_to_include(exclusion_rules, include_rules_by_item, project):
    included = sorted(include_rules_by_item)
    excluded = []
    collected = []
    for item in included:
        relative_path = item.relative_to(project)
        matching_exclusions = [rule for path in (relative_path, *relative_path.parents) if path != Path(".") for rule in exclusion_rules if path.full_match(rule)]
        most_specific_include = max(map(_rule_specificity, include_rules_by_item[item]))
        most_specific_exclusion = max(map(_rule_specificity, matching_exclusions), default=None)

        if most_specific_exclusion is not None and most_specific_exclusion > most_specific_include:
            excluded.append(item)
        else:
            collected.append(item)

    if excluded:
        logger.info("Dropping %d project items due to exclusion rules", len(excluded))
    logger.info("Collecting %d project items", len(collected))

    return collected


def ensure_required_files(collected, project: Path):
    """Add known project files, creating minimal build metadata when needed."""
    pyproject = project / "pyproject.toml"
    requirements = project / "requirements.txt"
    readme = next(
        (file for file in project.iterdir() if file.is_file() and file.name.casefold() == "readme.md"),
        project / "readme.md",
    )

    configuration = pyproject if pyproject.is_file() else requirements if requirements.is_file() else None
    if configuration is None:
        project_name = "-".join(part for part in "".join(character.lower() if character.isascii() and character.isalnum() else "-" for character in project.name).split("-") if part) or "ivaldi-project"
        logger.warning(
            "No pyproject.toml or requirements.txt found in %s; creating a minimal pyproject.toml and readme.md",
            project,
        )
        pyproject.write_text(
            f'[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"\n\n[project]\nname = "{project_name}"\nversion = "0.0.0"\nreadme = "{readme.name}"\n',
            encoding="utf-8",
        )
        if not readme.is_file():
            readme.write_text(f"# {project.name}\n", encoding="utf-8")
        configuration = pyproject

    for file in (configuration, readme):
        if file.is_file() and file not in collected:
            collected.append(file)

    return collected


def collect(settings):
    project = settings.dirs.project

    exclusion_rules, include_rules_by_item = build_rules(settings)
    collected = collect_files_to_include(exclusion_rules, include_rules_by_item, project)
    collected = ensure_required_files(collected, project)

    for item in collected:
        relative_path = item.relative_to(project)
        build_path = settings.dirs.stage / relative_path

        if item.is_dir():
            build_path.mkdir(parents=True, exist_ok=True)
            continue

        build_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, build_path, follow_symlinks=False)

    return collected
