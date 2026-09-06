"""Espanso config validation for espansr.

Validates templates for Espanso-incompatible patterns before syncing.
Checks trigger format, variable references, and cross-template uniqueness.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from espansr.core.command_catalog import COMMANDS_POPUP_TRIGGER
from espansr.core.config import get_config
from espansr.core.templates import Template, get_template_manager

logger = logging.getLogger(__name__)

# Regex to find {{var}} placeholders in template content
_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass
class ValidationWarning:
    """A validation issue found in a template.

    Attributes:
        severity: "error" (blocks sync) or "warning" (informational).
        message: Human-readable description of the issue.
        template_name: Name of the template with the issue.
    """

    severity: str
    message: str
    template_name: str


def validate_template(template: Template) -> List[ValidationWarning]:
    """Validate a single template for Espanso compatibility.

    Checks:
    - Trigger is not empty
    - Trigger is at least 2 characters
    - Trigger starts with ':' or '/' (Espanso convention)
    - Content placeholders have matching variables
    - Defined variables are referenced in content

    Args:
        template: The template to validate.

    Returns:
        List of ValidationWarning objects (empty if template is valid).
    """
    warnings: List[ValidationWarning] = []
    name = template.name

    # ── Trigger checks ───────────────────────────────────────────────────
    trigger = template.trigger

    if not trigger:
        warnings.append(
            ValidationWarning(
                severity="error",
                message="Trigger is empty",
                template_name=name,
            )
        )
    else:
        if len(trigger) < 2:
            warnings.append(
                ValidationWarning(
                    severity="error",
                    message=f"Trigger '{trigger}' is too short (minimum 2 characters)",
                    template_name=name,
                )
            )

        if not trigger.startswith(":") and not trigger.startswith("/"):
            warnings.append(
                ValidationWarning(
                    severity="warning",
                    message=(
                        f"Trigger '{trigger}' does not start with ':' or '/'; "
                        "Espanso keyword triggers conventionally start with ':'"
                    ),
                    template_name=name,
                )
            )

    # ── Variable checks ──────────────────────────────────────────────────
    content = template.content or ""
    placeholders = set(_PLACEHOLDER_RE.findall(content))
    defined_vars = {v.name for v in (template.variables or [])}

    # Placeholders without matching variables
    for placeholder in sorted(placeholders - defined_vars):
        warnings.append(
            ValidationWarning(
                severity="warning",
                message=(
                    f"Placeholder '{{{{{placeholder}}}}}' in content has no "
                    "matching variable defined"
                ),
                template_name=name,
            )
        )

    # Variables defined but not referenced in content
    for var_name in sorted(defined_vars - placeholders):
        warnings.append(
            ValidationWarning(
                severity="warning",
                message=f"Variable '{var_name}' is defined but never referenced in content",
                template_name=name,
            )
        )

    return warnings


def validate_all(espanso_config_dir: Optional[Path] = None) -> List[ValidationWarning]:
    """Validate all triggered templates, including cross-template checks.

    Runs validate_template() on each template and additionally checks
    for duplicate triggers across templates, non-blocking collisions with
    espansr-managed system triggers, and (read-only) collisions with triggers
    defined in the user's other Espanso ``match/*.yml`` files.

    Args:
        espanso_config_dir: Espanso config directory whose ``match/`` files are
            scanned; resolved automatically when None.

    Returns:
        List of all ValidationWarning objects found.
    """
    manager = get_template_manager()
    templates = list(manager.iter_with_triggers())

    warnings: List[ValidationWarning] = []

    # Per-template validation
    for template in templates:
        warnings.extend(validate_template(template))

    # Cross-template: duplicate triggers
    trigger_map: dict[str, list[str]] = {}
    for template in templates:
        if template.trigger:
            trigger_map.setdefault(template.trigger, []).append(template.name)

    for trigger, names in trigger_map.items():
        if len(names) > 1:
            for template_name in names:
                warnings.append(
                    ValidationWarning(
                        severity="error",
                        message=(
                            f"Duplicate trigger '{trigger}' — also used by: "
                            f"{', '.join(n for n in names if n != template_name)}"
                        ),
                        template_name=template_name,
                    )
                )

    warnings.extend(_system_trigger_collision_warnings(templates))
    warnings.extend(_capability_id_duplicate_warnings(templates))
    warnings.extend(_external_match_file_warnings(templates, espanso_config_dir))

    return warnings


def _system_triggers() -> dict[str, str]:
    """Map each generated system trigger to a human-readable role."""
    config = get_config()
    launcher_trigger = config.espanso.launcher_trigger or ":aopen"
    sync_trigger = getattr(config.espanso, "sync_trigger", "") or ":sync"
    return {
        launcher_trigger: "generated launcher trigger",
        COMMANDS_POPUP_TRIGGER: "generated commands popup trigger",
        sync_trigger: "generated sync trigger",
    }


def _collect_external_triggers(match_dir: Path, managed_names: set[str]) -> dict[str, list[str]]:
    """Read-only scan of the user's own ``match/*.yml`` files for their triggers.

    Skips espansr-managed files. A file that cannot be read or parsed is
    logged and skipped; this pass never fails hard.
    """
    import yaml

    external: dict[str, list[str]] = {}
    try:
        candidates = sorted(list(match_dir.glob("*.yml")) + list(match_dir.glob("*.yaml")))
    except OSError as exc:
        logger.warning("Could not list Espanso match files in %s: %s", match_dir, exc)
        return external

    for path in candidates:
        if path.name in managed_names:
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            logger.warning("Skipping unreadable Espanso match file %s: %s", path, exc)
            continue
        if not isinstance(data, dict):
            continue
        matches = data.get("matches")
        if not isinstance(matches, list):
            continue
        for entry in matches:
            if not isinstance(entry, dict):
                continue
            triggers: list = []
            single = entry.get("trigger")
            if isinstance(single, str) and single:
                triggers.append(single)
            multiple = entry.get("triggers")
            if isinstance(multiple, list):
                triggers.extend(t for t in multiple if isinstance(t, str) and t)
            for trigger in triggers:
                files = external.setdefault(trigger, [])
                if path.name not in files:
                    files.append(path.name)
    return external


def _external_match_file_warnings(
    templates: list[Template],
    espanso_config_dir: Optional[Path] = None,
) -> List[ValidationWarning]:
    """Warn when another Espanso match file defines one of espansr's triggers.

    Espanso loads every ``match/*.yml``; a trigger defined twice expands
    unpredictably. This is warning-only and read-only: nothing is modified and
    an unreadable file is skipped.
    """
    # Lazy import: espansr.integrations.espanso imports this module.
    from espansr.integrations import espanso as espanso_integration

    if espanso_config_dir is None:
        try:
            espanso_config_dir = espanso_integration.get_espanso_config_dir()
        except Exception as exc:  # detection must never break validation
            logger.warning("Could not resolve the Espanso config directory: %s", exc)
            return []
    if espanso_config_dir is None:
        return []

    match_dir = Path(espanso_config_dir) / "match"
    managed_names = set(espanso_integration._MANAGED_FILES) | set(
        espanso_integration._OLD_MANAGED_FILES
    )
    external = _collect_external_triggers(match_dir, managed_names)
    if not external:
        return []

    warnings: List[ValidationWarning] = []
    for template in templates:
        files = external.get(template.trigger)
        if files:
            warnings.append(
                ValidationWarning(
                    severity="warning",
                    message=(
                        f"Trigger '{template.trigger}' is also defined in Espanso match "
                        f"file(s) {', '.join(files)}; Espanso will expand only one of them"
                    ),
                    template_name=template.name,
                )
            )
    for trigger, role in _system_triggers().items():
        files = external.get(trigger)
        if files:
            warnings.append(
                ValidationWarning(
                    severity="warning",
                    message=(
                        f"Trigger '{trigger}' ({role}) is also defined in Espanso match "
                        f"file(s) {', '.join(files)}; Espanso will expand only one of them"
                    ),
                    template_name="system",
                )
            )
    return warnings


def _capability_id_duplicate_warnings(templates: list[Template]) -> List[ValidationWarning]:
    """Warn when two templates declare the same explicit capability ID.

    Capability IDs are stable identities referenced by workflow manifests, so
    duplicates make workflow membership ambiguous. This is warning-only: it
    never blocks Espanso publishing, which does not depend on capability IDs.
    """
    id_map: dict[str, list[str]] = {}
    for template in templates:
        cap_id = getattr(template, "capability_id", "")
        if cap_id:
            id_map.setdefault(cap_id, []).append(template.name)

    warnings: List[ValidationWarning] = []
    for cap_id, names in id_map.items():
        if len(names) > 1:
            for template_name in names:
                warnings.append(
                    ValidationWarning(
                        severity="warning",
                        message=(
                            f"Duplicate capability ID '{cap_id}' — also declared by: "
                            f"{', '.join(n for n in names if n != template_name)}"
                        ),
                        template_name=template_name,
                    )
                )
    return warnings


def _system_trigger_collision_warnings(templates: list[Template]) -> List[ValidationWarning]:
    """Return warning-only issues for collisions with generated system triggers."""
    config = get_config()
    if config.espanso.allow_system_trigger_collisions:
        return []

    launcher_trigger = config.espanso.launcher_trigger or ":aopen"
    system_triggers = _system_triggers()

    warnings: List[ValidationWarning] = []
    if launcher_trigger == COMMANDS_POPUP_TRIGGER:
        warnings.append(
            ValidationWarning(
                severity="warning",
                message=(
                    f"System trigger collision: launcher trigger '{launcher_trigger}' "
                    "also opens the commands popup; set "
                    "espanso.allow_system_trigger_collisions to true to acknowledge"
                ),
                template_name="system",
            )
        )

    for template in templates:
        system_role = system_triggers.get(template.trigger)
        if system_role:
            warnings.append(
                ValidationWarning(
                    severity="warning",
                    message=(
                        f"Trigger '{template.trigger}' collides with the {system_role}; set "
                        "espanso.allow_system_trigger_collisions to true to acknowledge"
                    ),
                    template_name=template.name,
                )
            )

    return warnings
