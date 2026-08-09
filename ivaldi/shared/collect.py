import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _rule_specificity(rule):
    """Rank path rules by how narrowly they describe a path."""
    literal_characters = sum(character not in "*?[]" for character in rule)
    wildcard_characters = sum(character in "*?[]" for character in rule)
    return literal_characters, -wildcard_characters, len(rule)


def collect(settings):
    project = settings.dirs.project
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
        for item in project.glob(rule):
            include_rules_by_item.setdefault(item, []).append(rule)

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

    logger.info("Collecting %d project items", len(collected))
    if excluded:
        logger.info("Dropping %d project items due to exclusion rules", len(excluded))

    collected.append(project / "pyproject.toml")
    for item in collected:
        relative_path = item.relative_to(project)
        build_path = settings.dirs.stage / relative_path

        if item.is_dir():
            build_path.mkdir(parents=True, exist_ok=True)
            continue

        build_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, build_path, follow_symlinks=False)

    return collected
