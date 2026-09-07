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

# Every user-facing CLI subcommand. ``record-install`` is installer-only and is
# deliberately left out; ``tests/test_discovery_sync.py`` checks the rest.
_CLI: List[Entry] = [
    ("publish", "publish local templates to Espanso"),
    ("pull", "pull remote templates and refresh Espanso"),
    ("push", "push local templates to the remote"),
    ("sync", "pull, push local changes, and reinstall"),
    ("starters", "reconcile bundled starter templates"),
    ("retire", "back up and delete a template"),
    ("remote", "manage the template Git remote"),
    ("list", "show templates with triggers"),
    ("status", "show config paths"),
    ("setup", "run post-install setup"),
    ("doctor", "run diagnostic health checks"),
    ("validate", "check for errors"),
    ("import", "import templates"),
    ("gui", "launch editor"),
    ("refresh", "reinstall espansr in place"),
    ("workflows", "inspect optional workflow manifests"),
    ("packet", "inspect saved handoff packets"),
    ("check-output", "validate a model output against a note's output contract"),
    ("completions", "print a shell completion script"),
    ("wsl-install-espanso", "WSL helper: install and start Espanso on Windows"),
    ("configure-remote-desktop", "tune Espanso for RustDesk/RDP; --revert restores"),
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

# One row per generated system trigger (see :data:`SYSTEM_TRIGGERS`).
_DISCOVERY: List[Entry] = [
    (":aopen", "open the full espansr editor"),
    (":coms", "open the live command popup"),
    (":espansr", "expand this static quick reference"),
    (":sync", "pull, push, and reinstall espansr"),
]

_FOOTER = "\n".join(
    [
        "Config: Linux/WSL ~/.config/espansr/",
        "        Windows   %APPDATA%\\espansr\\",
        "        macOS     ~/Library/Application Support/espansr/",
        "        (espansr status prints the active path)",
        "Publish: espansr publish",
        "Remote:  espansr pull / espansr push",
    ]
)


def _label_width(rows: List[Entry]) -> int:
    """Column width that keeps the dashes of *rows* aligned."""
    return max(len(label) for label, _ in rows)


# ── Prompt notes: the single source both static surfaces render from ─────────

PROMPT_SECTIONS: Tuple[HelpSection, ...] = (
    HelpSection(
        "Agent feature prompts",
        22,
        (
            (":project-init-llm", "initialize AGENTS.md-centered repo instructions"),
            (":feature", "three-outcome implementation meta-prompt or project-native flow"),
            (":cb-transcript-feature", "transcript to implementation-ready feature specs"),
        ),
    ),
    HelpSection(
        "Project and maintenance prompts",
        17,
        (
            (":goal", "interpret, gap-check, and refine context into a measurable goal"),
            (
                ":show-me",
                "ingest, clarify, enrich, and return work so the next reader can act alone",
            ),
            (
                ":troubleshoot",
                "debug with context checks, research, planning, fixing, and verification",
            ),
            (":continue", "resume work in flight and keep going to done or a real gate"),
            (":unblock", "clear blockers with bulk decisions and safe actions"),
            (":verify", "verify, repair, and align affected docs"),
            (
                ":adversary-review",
                "adversarial review of finished work against its spec, with a verdict",
            ),
            (":litmus", "create or audit a plain-language human-verification checklist"),
            (
                ":feedback",
                "apply current-cycle feedback to the existing project and verify the changes",
            ),
            (":docs-qa", "docs-only alignment fallback"),
            (
                ":work-merge",
                "sanitize, verify, then merge and push only when the repo state is safe",
            ),
        ),
    ),
    HelpSection(
        "Personal program prompts",
        24,
        (
            (
                ":project-personal-growth",
                "guide Personal Growth sessions and keep the program records true",
            ),
            (
                ":project-systems",
                "coordinate and watch the Master Systems Process from its owning files",
            ),
            (
                ":project-decision-helper",
                "reason through a decision aligned to your values while you keep the choice",
            ),
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
        ),
    ),
    HelpSection(
        "Explanation, research, and analysis prompts",
        17,
        (
            (":q&a", "start evidence-bound Q&A on the current context"),
            (":explain", "explain context or sources in a faithful one-page summary"),
            (":visual", "build workflow diagrams or visual explanations"),
            (
                ":reality-max",
                "full account of what was done or would happen, with tables and diagrams",
            ),
            (
                ":reality-min",
                "one or two sentences and up to ten bullets on exactly what was done",
            ),
            (":gaps", "critical review modes for gaps and principles"),
            (":meta", "context-safe meta-prompt generator"),
            (":context", "condense drifted prompt context"),
            (":template-builder", "draft command templates"),
            (":sanitize", "assess sensitive/internal traces and recommend sanitization"),
            (":research", "research a topic with strong evidence handling and synthesis"),
            (":audit", "build an interactive HTML audit/decision packet to resolve findings"),
            (
                ":html-help-doc",
                "build an interactive HTML runbook with result tracking and model-ready copy-back",
            ),
            (
                ":ui-ux-audit",
                "audit screens, flows, and states against a standalone usability baseline",
            ),
            (":cb-agenda", "turn project context into an email-ready meeting agenda"),
        ),
    ),
    HelpSection(
        "Source and capture prompts",
        9,
        ((":telegram", "run the directive from an accessible source or location"),),
    ),
    HelpSection(
        "Utility prompts",
        9,
        (
            (":tddh", "think deeply, verify facts, and never make things up"),
            (":listen", "convert research to listenable article"),
            (":revise", "clean up messaging while preserving meaning and direction"),
            (":cliche", "remove AI clichés and restore natural prose"),
        ),
    ),
    HelpSection(
        "File helpers",
        15,
        (
            (
                ":pocket-extract",
                "PowerShell: unpack note archives and collect renamed transcription files",
            ),
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
        _render_rows("espansr CLI commands", _CLI, _label_width(_CLI)),
        _LIFECYCLE,
        _render_rows("Discovery", _DISCOVERY, _label_width(_DISCOVERY)),
    ]
    for section in PROMPT_SECTIONS:
        blocks.append(_render_rows(section.title, list(section.entries), section.width))
    blocks.append(_FOOTER)
    return "\n\n".join(blocks) + "\n\n"


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
