"""Shared trigger catalog for the commands popup."""

from dataclasses import dataclass
from typing import Iterable, Optional

from espansr.core.config import Config, get_config
from espansr.core.templates import Template, TemplateManager, get_template_manager

COMMANDS_POPUP_TRIGGER = ":coms"
COMMANDS_POPUP_NAME = "Command Reference"
COMMANDS_POPUP_DESCRIPTION = "Show a quick popup of your available Espanso triggers."
COMMANDS_POPUP_PREVIEW = (
    "Opens a scrollable popup with your current Espanso triggers, "
    "descriptions, and output previews."
)
LAUNCHER_NAME = "Open Editor"
LAUNCHER_DESCRIPTION = "Launch the full espansr editor window."
LAUNCHER_PREVIEW = "Opens the full espansr editor so you can browse, edit, and sync templates."

_PREVIEW_MAX_LINES = 4
_PREVIEW_MAX_CHARS = 280


@dataclass(frozen=True)
class CommandCatalogEntry:
    """Normalized row model for the commands popup."""

    trigger: str
    name: str
    description: str
    preview: str
    source: str


def _placeholder_value(var) -> str:
    """Return a stable placeholder value for preview rendering."""
    if getattr(var, "default", ""):
        return var.default
    label = getattr(var, "label", "") or getattr(var, "name", "value")
    return f"[{label}]"


def _truncate_preview(text: str) -> str:
    """Clamp preview text to a small, readable block for the popup."""
    normalized = "\n".join(line.rstrip() for line in (text or "").replace("\r\n", "\n").split("\n"))
    normalized = normalized.strip()
    if not normalized:
        return "(No output preview available)"

    lines = normalized.split("\n")
    if len(lines) > _PREVIEW_MAX_LINES:
        lines = lines[:_PREVIEW_MAX_LINES]
        lines[-1] = lines[-1].rstrip() + "..."
        normalized = "\n".join(lines)

    if len(normalized) > _PREVIEW_MAX_CHARS:
        normalized = normalized[: _PREVIEW_MAX_CHARS - 3].rstrip() + "..."

    return normalized


def _build_template_preview(template: Template) -> str:
    """Render a stable preview for a template row."""
    values = {var.name: _placeholder_value(var) for var in (template.variables or [])}
    return _truncate_preview(template.render(values))


def _iter_template_entries(template_manager: TemplateManager) -> Iterable[CommandCatalogEntry]:
    """Yield popup entries for template-backed triggers."""
    for template in template_manager.iter_with_triggers():
        yield CommandCatalogEntry(
            trigger=template.trigger,
            name=template.name,
            description=(template.description or template.name).strip(),
            preview=_build_template_preview(template),
            source="template",
        )


def _build_system_entries(config: Config) -> list[CommandCatalogEntry]:
    """Return built-in entries that are available outside template sync."""
    launcher_trigger = config.espanso.launcher_trigger or ":aopen"
    return [
        CommandCatalogEntry(
            trigger=launcher_trigger,
            name=LAUNCHER_NAME,
            description=LAUNCHER_DESCRIPTION,
            preview=LAUNCHER_PREVIEW,
            source="system",
        ),
        CommandCatalogEntry(
            trigger=COMMANDS_POPUP_TRIGGER,
            name=COMMANDS_POPUP_NAME,
            description=COMMANDS_POPUP_DESCRIPTION,
            preview=COMMANDS_POPUP_PREVIEW,
            source="system",
        ),
    ]


def build_command_catalog(
    template_manager: Optional[TemplateManager] = None,
    config: Optional[Config] = None,
) -> list[CommandCatalogEntry]:
    """Build the complete trigger catalog for the commands popup."""
    template_manager = template_manager or get_template_manager()
    config = config or get_config()

    entries = list(_iter_template_entries(template_manager))
    entries.extend(_build_system_entries(config))
    return sorted(entries, key=lambda entry: (entry.trigger.lower(), entry.name.lower()))
