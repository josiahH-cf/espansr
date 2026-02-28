"""Espanso config validation for espansr.

Validates templates for Espanso-incompatible patterns before syncing.
Checks trigger format, variable references, and cross-template uniqueness.
"""

import re
from dataclasses import dataclass
from typing import List

from espansr.core.templates import Template, get_template_manager

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


def validate_all() -> List[ValidationWarning]:
    """Validate all triggered templates, including cross-template checks.

    Runs validate_template() on each template and additionally checks
    for duplicate triggers across templates.

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

    return warnings
