"""Shared trigger catalog for the commands popup."""

from dataclasses import dataclass
from typing import Iterable, Optional

from espansr.core.config import Config, get_config
from espansr.core.templates import Template, TemplateManager

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
SYNC_TRIGGER = ":sync"
SYNC_NAME = "Sync & Reinstall"
SYNC_DESCRIPTION = "Pull the latest version, push local changes if clean, then reinstall locally."
SYNC_PREVIEW = (
    "Runs `espansr sync`: rebases the project repo onto the latest, pushes your local "
    "changes when there is no conflict, then reruns the installer recorded at first install."
)

_PREVIEW_MAX_LINES = 4
_PREVIEW_MAX_CHARS = 280


@dataclass(frozen=True)
class CommandCatalogEntry:
    """Normalized row model for the commands popup.

    Capability metadata and workflow membership are additive, defaulted
    fields: they power intent- and artifact-aware discovery while leaving
    every existing consumer untouched. ``workflow_next`` holds derived
    (trigger, edge label) neighbors from workflow manifests — derived at
    runtime, never written back to templates.
    """

    trigger: str
    name: str
    description: str
    preview: str
    source: str
    category: str = ""
    stage: str = ""
    next_triggers: tuple[str, ...] = ()
    capability_id: str = ""
    intent_tags: tuple[str, ...] = ()
    accepts: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    use_when: str = ""
    avoid_when: str = ""
    workflows: tuple[str, ...] = ()
    workflow_next: tuple[tuple[str, str], ...] = ()
    has_output_contract: bool = False
    content: str = ""

    @property
    def workflow_label(self) -> str:
        """Return the compact category/stage label shown in discovery surfaces."""
        parts = [part for part in (self.category, self.stage) if part]
        return " / ".join(parts) if parts else self.source

    @property
    def next_label(self) -> str:
        """Return a compact next-step hint for workflow-aware prompts."""
        if not self.next_triggers:
            return ""
        return "Next: " + ", ".join(self.next_triggers)


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
    from espansr.core.capabilities import effective_capability_id

    for template in template_manager.iter_with_triggers():
        yield CommandCatalogEntry(
            trigger=template.trigger,
            name=template.name,
            description=(template.description or template.name).strip(),
            preview=_build_template_preview(template),
            source="template",
            category=template.category or "template",
            stage=template.stage or "custom",
            next_triggers=tuple(template.next_triggers or []),
            capability_id=effective_capability_id(template),
            intent_tags=tuple(template.intent_tags or []),
            accepts=tuple(template.accepts or []),
            produces=tuple(template.produces or []),
            use_when=template.use_when or "",
            avoid_when=template.avoid_when or "",
            has_output_contract=bool(template.output_contract),
            content=template.content or "",
        )


def _build_system_entries(config: Config) -> list[CommandCatalogEntry]:
    """Return built-in entries that are available outside template sync."""
    launcher_trigger = config.espanso.launcher_trigger or ":aopen"
    sync_trigger = getattr(config.espanso, "sync_trigger", "") or SYNC_TRIGGER
    return [
        CommandCatalogEntry(
            trigger=launcher_trigger,
            name=LAUNCHER_NAME,
            description=LAUNCHER_DESCRIPTION,
            preview=LAUNCHER_PREVIEW,
            source="system",
            category="system",
            stage="launcher",
        ),
        CommandCatalogEntry(
            trigger=COMMANDS_POPUP_TRIGGER,
            name=COMMANDS_POPUP_NAME,
            description=COMMANDS_POPUP_DESCRIPTION,
            preview=COMMANDS_POPUP_PREVIEW,
            source="system",
            category="system",
            stage="reference",
        ),
        CommandCatalogEntry(
            trigger=sync_trigger,
            name=SYNC_NAME,
            description=SYNC_DESCRIPTION,
            preview=SYNC_PREVIEW,
            source="system",
            category="system",
            stage="maintenance",
        ),
    ]


def _attach_workflow_membership(
    entries: list[CommandCatalogEntry], workflow_catalog
) -> list[CommandCatalogEntry]:
    """Enrich entries with workflow membership and derived neighbors.

    Neighbors are derived from manifest edges at runtime and mapped to the
    current triggers via each capability's stable ID. Nothing is written back
    to template files — topology stays owned by the manifests.
    """
    from dataclasses import replace

    trigger_by_capability = {
        entry.capability_id: entry.trigger for entry in entries if entry.capability_id
    }
    enriched: list[CommandCatalogEntry] = []
    for entry in entries:
        if not entry.capability_id:
            enriched.append(entry)
            continue
        memberships = tuple(
            workflow.id for workflow in workflow_catalog.workflows_for(entry.capability_id)
        )
        neighbors = tuple(
            (trigger_by_capability[edge.target], edge.label)
            for _workflow, edge in workflow_catalog.outgoing(entry.capability_id)
            if edge.target in trigger_by_capability
        )
        if memberships or neighbors:
            entry = replace(entry, workflows=memberships, workflow_next=neighbors)
        enriched.append(entry)
    return enriched


def build_command_catalog(
    template_manager: Optional[TemplateManager] = None,
    config: Optional[Config] = None,
    workflow_catalog=None,
) -> list[CommandCatalogEntry]:
    """Build the complete trigger catalog for the commands popup."""
    # Always create a fresh TemplateManager to avoid stale singleton state.
    # The cached get_template_manager() singleton fixes templates_dir at
    # creation time; bypassing it ensures every catalog build re-derives
    # the templates directory from the current config state and reads
    # the most recent files from disk.
    template_manager = template_manager or TemplateManager()
    config = config or get_config()

    entries = list(_iter_template_entries(template_manager))
    if workflow_catalog is None:
        from espansr.core.workflows import load_workflow_catalog

        workflow_catalog = load_workflow_catalog()
    entries = _attach_workflow_membership(entries, workflow_catalog)
    entries.extend(_build_system_entries(config))
    return sorted(entries, key=lambda entry: (entry.trigger.lower(), entry.name.lower()))
