"""Single source of truth for the espansr command-discovery surfaces.

Both static discovery surfaces are rendered from the data in this module:

- the ``:espansr`` quick-help text (published as ``templates/espansr_help.json``)
- the bundled prompt-note list in ``docs/TEMPLATES.md``

Because both surfaces are generated from :data:`PROMPT_SECTIONS`, they cannot
drift from each other. ``tests/test_discovery_sync.py`` additionally asserts
that every bundled template trigger appears here, so adding a note surfaces it
everywhere automatically. Regenerate the files with ``scripts/sync_discovery.py``.

The live ``:coms`` popup is already generated from the templates at runtime
(see :mod:`espansr.core.command_catalog`); this module keeps the two *static*
surfaces in lockstep with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

# Em dash used to separate a trigger/command from its one-line blurb.
DASH = "\u2014"

# Triggers that espansr generates itself; they are not prompt notes and are
# excluded from the docs prompt-note list.
SYSTEM_TRIGGERS: Tuple[str, ...] = (":aopen", ":coms", ":espansr", ":sync")

# (label, blurb) row shown in the quick help.
Entry = Tuple[str, str]


@dataclass(frozen=True)
class HelpSection:
    """A titled group of prompt-note rows in the quick help."""

    title: str
    width: int
    entries: Tuple[Entry, ...]


def _render_rows(title: str, rows: List[Entry], width: int) -> str:
    """Render a titled block of ``label - blurb`` rows with aligned dashes."""
    out = [f"{title}:"]
    for label, blurb in rows:
        out.append(f"  {label.ljust(width)} {DASH} {blurb}")
    return "\n".join(out)


# ── Static scaffolding (not prompt notes) ────────────────────────────────────

_CLI: List[Entry] = [
    ("publish", "publish local templates to Espanso"),
    ("pull", "pull remote templates and refresh Espanso"),
    ("push", "push local templates to the remote"),
    ("starters", "reconcile bundled starter templates"),
    ("retire", "back up and delete a template"),
    ("remote", "manage the template Git remote"),
    ("list", "show templates with triggers"),
    ("status", "show config paths"),
    ("setup", "run post-install setup"),
    ("validate", "check for errors"),
    ("import", "import templates"),
    ("gui", "launch editor"),
    ("refresh", "reinstall espansr in place"),
]

_LIFECYCLE = "\n".join(
    [
        "Template lifecycle:",
        "  Create:   espansr gui or espansr import file.json",
        "  Check:    espansr validate",
        "  Publish:  espansr publish",
        "  Retire:   espansr retire TARGET",
        "  Starters: espansr starters --apply",
    ]
)

_DISCOVERY: List[Entry] = [
    (":coms", "open the live command popup"),
    (":espansr", "expand this static quick reference"),
]

_FOOTER = "\n".join(
    [
        "Config: ~/.config/espansr/",
        "Publish: espansr publish",
        "Remote:  espansr pull / espansr push",
    ]
)

# ── Prompt notes: the single source both static surfaces render from ─────────

PROMPT_SECTIONS: Tuple[HelpSection, ...] = (
    HelpSection(
        "Agent feature workflow",
        17,
        (
            (":project-init-llm", "initialize AGENTS.md-centered repo instructions"),
            (":agent-scaffold", "create the persistent features/ loop"),
            (":feat-plan", "add or refine feature scope without implementation"),
            (":feat-runner", "start or continue the current or next feature"),
            (":feat", "route older feature workflow requests to the split commands"),
            (":feedback-loop", "run an autonomous feedback loop into verified feature specs"),
        ),
    ),
    HelpSection(
        "Prompt workflow",
        13,
        (
            (":goal", "clarify a vague goal into milestones"),
            (
                ":troubleshoot",
                "debug with context checks, research, planning, fixing, and verification",
            ),
            (":verify", "verify, repair, and align affected docs"),
            (":docs-qa", "docs-only alignment fallback"),
            (":save", "save project state for next session"),
            (":merge", "safely merge and push relevant changes"),
            (":work-merge-safe", "sanitize, verify, merge, and push only when state is safe"),
        ),
    ),
    HelpSection(
        "Git helpers",
        15,
        (
            (":git-yolo-sh", "Bash yolo commit, update main when needed, and push safely"),
            (":git-rebase-sh", "Bash safe main update or branch rebase with stash restore"),
            (":git-branch-sh", "Bash update main when safe, then create and switch to a branch"),
            (":git-yolo-ps", "PowerShell yolo commit, update main when needed, and push safely"),
            (":git-rebase-ps", "PowerShell safe main update or branch rebase with stash restore"),
            (
                ":git-branch-ps",
                "PowerShell update main when safe, then create and switch to a branch",
            ),
            (":rebase", "safely inspect branch state and rebase current work when clear"),
        ),
    ),
    HelpSection(
        "Explanation, research, and analysis prompts",
        17,
        (
            (":explain", "explain context in plain, evidence-bound terms"),
            (":visual", "build workflow diagrams or visual explanations"),
            (":gaps", "critical review modes for gaps, principles, and reality audits"),
            (":meta", "context-safe meta-prompt generator"),
            (":context", "condense drifted prompt context"),
            (":template-builder", "draft command templates"),
            (":sanitize", "assess sensitive/internal traces and recommend sanitization"),
            (":distill", "distill long context into a 3-paragraph objective synopsis"),
            (":research", "research a topic with strong evidence handling and synthesis"),
            (":summarize", "summarize one source with grounded facts and core insights"),
            (":audit", "build an interactive HTML audit/decision packet to resolve findings"),
        ),
    ),
    HelpSection(
        "Pocket capture prompts",
        14,
        (
            (":pocket-note", "run the project's contextualized.md note in this codebase"),
            (":pocket-system", "sync Pocket notes into Obsidian and run a directive on one"),
        ),
    ),
    HelpSection(
        "Utility prompts",
        9,
        (
            (":defaults", "set default working style"),
            (":listen", "convert research to listenable article"),
            (":revise", "clean up messaging while preserving meaning and direction"),
        ),
    ),
    HelpSection(
        "Security helpers",
        14,
        ((":tenable-scans", "PowerShell: unpack and normalize Tenable .nessus scan archives"),),
    ),
)


def render_quick_help() -> str:
    """Render the full ``:espansr`` quick-help text."""
    blocks = [
        _render_rows("espansr CLI commands", _CLI, 8),
        _LIFECYCLE,
        _render_rows("Discovery", _DISCOVERY, 8),
    ]
    for section in PROMPT_SECTIONS:
        blocks.append(_render_rows(section.title, list(section.entries), section.width))
    blocks.append(_FOOTER)
    return "\n\n".join(blocks)


def render_docs_note_list() -> str:
    """Render the grouped prompt-note list embedded in ``docs/TEMPLATES.md``."""
    lines = []
    for section in PROMPT_SECTIONS:
        triggers = ", ".join(f"`{trigger}`" for trigger, _ in section.entries)
        lines.append(f"- {section.title}: {triggers}")
    return "\n".join(lines)


def prompt_note_triggers() -> List[str]:
    """Return every prompt-note trigger listed in the discovery surfaces."""
    return [trigger for section in PROMPT_SECTIONS for trigger, _ in section.entries]
