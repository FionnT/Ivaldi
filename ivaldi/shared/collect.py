import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


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

    included = set()
    for rule in settings.app.include:
        included.update(project.glob(rule))

    included = sorted(included)
    excluded = []
    collected = []

    for item in included:
        relative_path = item.relative_to(project)
        relative_or_parent_excluded = any(
            path.full_match(rule)
            for path in (relative_path, *relative_path.parents)
            if path != Path(".")
            for rule in exclusion_rules
        )

        if relative_or_parent_excluded:
            excluded.append(item)
        else:
            collected.append(item)

    logger.info("Collecting %d project items", len(collected))
    if excluded:
        logger.info("Dropping %d project items due to exclusion rules", len(excluded))

    for item in collected:
        relative_path = item.relative_to(project)
        build_path = settings.dirs.build / relative_path

        if item.is_dir():
            build_path.mkdir(parents=True, exist_ok=True)
            continue

        build_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, build_path, follow_symlinks=False)

    return collected
