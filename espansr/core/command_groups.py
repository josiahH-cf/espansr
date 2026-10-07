"""Curated, overlapping browse groups for the live command reference.

Membership uses capability IDs, including the documented file-stem fallback,
never trigger spellings. Workflow IDs refer to the existing manifest catalog;
relationships and combination guidance remain owned by those manifests.
Unknown commands are always reachable in the custom group and full catalog.
"""

from dataclasses import dataclass

from espansr.core.command_catalog import CommandCatalogEntry


@dataclass(frozen=True)
class CommandGroup:
    id: str
    title: str
    description: str
    capabilities: tuple[str, ...] = ()
    workflows: tuple[str, ...] = ()


COMMAND_GROUPS = (
    CommandGroup(
        "keep-moving",
        "Keep work moving",
        "Resume unfinished work, resolve blockers, apply feedback, or answer recommendations.",
        (
            "continue",
            "unblock",
            "context-reset",
            "feedback-apply",
            "fix_this",
            "troubleshooting",
            "use_recommendation",
            "accept_all_recommendations",
            "telegram",
        ),
        ("session-continuity",),
    ),
    CommandGroup(
        "carry-context",
        "Carry context & hand off",
        "Preserve what matters and prepare another session or model to do the next work.",
        ("context-reset", "meta", "human-litmus", "feature-handoff", "feature-clarification"),
        ("fresh-model-verification",),
    ),
    CommandGroup(
        "clarify-specs",
        "Clarify ideas & specs",
        "Turn rough thoughts or meeting notes into clear goals and ready feature specifications.",
        (
            "goal-refinement",
            "project-clarity",
            "feature-clarification",
            "feature-handoff",
            "spec-discovery",
            "gap-review",
            "use_recommendation",
            "accept_all_recommendations",
        ),
        ("feature-delivery-cycle",),
    ),
    CommandGroup(
        "research-challenge",
        "Research & challenge",
        "Gather evidence, ask grounded questions, challenge assumptions, or assess what exists.",
        (
            "research-report",
            "q_and_a",
            "tool-selection",
            "architecture-stabilization",
            "gap-review",
            "audit-packet",
            "deletion-simplification-audit",
            "tddh_defaults",
        ),
        ("evidence-research-cycle",),
    ),
    CommandGroup(
        "check-work",
        "Check & improve work",
        "Draft outcome checks, review work, walk real journeys, verify repairs, or cut test and "
        "upkeep friction.",
        (
            "human-litmus",
            "test-speed-optimization",
            "maintenance-friction",
            "verification",
            "adversarial-review",
            "canary_runner",
            "observed-journey",
            "experience-audit",
            "docs_qa",
            "feedback-apply",
            "audit-packet",
            "sanitize",
        ),
        ("fresh-model-verification", "feature-delivery-cycle"),
    ),
    CommandGroup(
        "explain-communicate",
        "Explain & communicate",
        "Understand the real situation and turn it into clear explanations, visuals, or messages.",
        (
            "explain_context_comprehensively",
            "show_me",
            "reality-max",
            "reality-min",
            "visual-workflow",
            "playbook",
            "html-help-doc",
            "speechify",
            "revise",
            "cliche",
            "cb_agenda",
        ),
        ("evidence-research-cycle",),
    ),
    CommandGroup(
        "create-assets",
        "Create images & prompts",
        "Create an image, reusable command template, or scoped prompt for future work.",
        ("image_generator", "template_builder", "meta"),
    ),
    CommandGroup(
        "personal-programs",
        "Personal programs",
        "Review finances, work through personal decisions or growth, or coordinate your systems.",
        ("finance_review", "project_personal_growth", "project_systems", "project_decision_helper"),
    ),
    CommandGroup(
        "tools-setup",
        "Git, setup & files",
        "Manage branches and delivery, initialize project instructions, or use local file helpers.",
        (
            "git_branch_ps",
            "git_branch_sh",
            "git_rebase_ps",
            "git_rebase_sh",
            "git_yolo_ps",
            "git_yolo_sh",
            "work_merge",
            "project_init_llm",
            "tenable_scans",
            "pocket_extract",
            "espansr_help",
            "espansr-launcher",
            "espansr-commands",
            "espansr-sync",
        ),
    ),
)

CUSTOM_GROUP = CommandGroup(
    "custom",
    "Custom / ungrouped",
    "Your other commands. Select one to see its description and prompt.",
)


# Role and recognition cue. These describe the bundled job; full, live template
# descriptions and use/avoid guidance remain visible in the selected detail.
_CUES = {
    "continue": (
        "Resume work",
        "Work is unfinished and you want the next supported action carried through.",
    ),
    "unblock": (
        "Resolve blockers",
        "A run left questions, omissions, approval claims, or other loose ends.",
    ),
    "context-reset": (
        "Carry context",
        "The conversation has grown or drifted and you need the relevant state for later.",
    ),
    "human-litmus": (
        "Draft checks",
        "A fresh model needs a project brief and observable checks of intended outcomes.",
    ),
    "verification": (
        "Verify & repair",
        "You want completed work checked against reality and clear problems repaired.",
    ),
    "adversarial-review": (
        "Review only",
        "You want an independent verdict on whether delivered work satisfies its spec.",
    ),
    "audit-packet": (
        "Assess & clarify",
        "You need evidence assessed and findings resolved through console clarification.",
    ),
    "deletion-simplification-audit": (
        "Review only",
        "You want recommendations on what to simplify, update, or remove.",
    ),
    "test-speed-optimization": (
        "Speed up tests",
        "Tests or CI take too long and you want measured, correctness-preserving speedups.",
    ),
    "maintenance-friction": (
        "Reduce friction",
        "Tests, installs, or instructions cost too much upkeep and you want only measured fixes.",
    ),
    "observed-journey": (
        "Walk a journey",
        "You want one real sample walked end to end and only the demonstrated gap fixed.",
    ),
    "experience-audit": (
        "Improve interface",
        "You want the interface assessed, improved, and verified.",
    ),
    "canary_runner": (
        "Exercise behavior",
        "You want a real canary run using synthetic data and cleanup afterward.",
    ),
    "docs_qa": ("Align docs", "Documentation needs alignment without a full verification pass."),
    "feedback-apply": (
        "Apply feedback",
        "You have feedback to apply to the current project and verify.",
    ),
    "fix_this": (
        "Repair issue",
        "The issue is already in context and you want its root cause fixed.",
    ),
    "troubleshooting": (
        "Diagnose & repair",
        "A failure needs investigation, fixing, and verification.",
    ),
    "goal-refinement": (
        "Clarify goal",
        "Your intention needs to become a bounded, measurable goal.",
    ),
    "tool-selection": (
        "Pick the right tool",
        "You have a result in mind and want the best existing skill, prompt, or tool chosen.",
    ),
    "architecture-stabilization": (
        "Stabilize architecture",
        "Logic is duplicated or bypasses its owner and you want one bounded fix handed off.",
    ),
    "project-clarity": (
        "See where it stands",
        "You want current truth against the end state and the next smallest useful result.",
    ),
    "feature-clarification": (
        "Write specs",
        "A batch of rough ideas needs dense clarification and finalized project specs.",
    ),
    "feature-handoff": (
        "Write spec",
        "A feature idea needs a grounded specification or implementation handoff.",
    ),
    "spec-discovery": (
        "Write specs",
        "Meeting notes or a transcript need to become ready feature specifications.",
    ),
    "meta": (
        "Draft prompt",
        "You need a scoped, context-safe prompt to give another model or session.",
    ),
    "research-report": (
        "Gather evidence",
        "You need researched evidence, synthesis, and clear uncertainty.",
    ),
    "q_and_a": (
        "Ask questions",
        "You want answers grounded in the project or material already available.",
    ),
    "gap-review": (
        "Challenge thinking",
        "You want gaps, weak assumptions, or first principles examined.",
    ),
    "tddh_defaults": (
        "Reliability cue",
        "You want to reinforce careful reasoning, fact checking, and honest uncertainty.",
    ),
    "use_recommendation": (
        "Answer one item",
        "Accept the current recommendation and continue, with optional added context.",
    ),
    "accept_all_recommendations": (
        "Answer a batch",
        "Accept all current recommendations and continue, with optional added context.",
    ),
    "sanitize": (
        "Review sharing",
        "Material needs assessment against its actual sharing boundary and sensitivity.",
    ),
    "explain_context_comprehensively": (
        "Explain",
        "You need a faithful one-page explanation of the context or source.",
    ),
    "show_me": (
        "Make clear",
        "The material needs a fuller, audience-aware explanation with useful examples or visuals.",
    ),
    "reality-max": (
        "Explain reality",
        "You need a detailed account of what exists or would actually happen.",
    ),
    "reality-min": (
        "Summarize reality",
        "You need a very short, grounded account of what is true or was done.",
    ),
    "visual-workflow": (
        "Diagram",
        "A diagram or visual explanation would make the relationships clearer.",
    ),
    "playbook": (
        "Write steps",
        "You need source-grounded instructions with plain, copyable steps.",
    ),
    "html-help-doc": (
        "Create runbook",
        "You want an interactive HTML help document with result tracking and copy-back.",
    ),
    "speechify": (
        "Prepare audio",
        "Research needs to become a complete, listenable text-to-speech article.",
    ),
    "revise": (
        "Refine wording",
        "Text needs clearer wording while preserving its meaning and tone.",
    ),
    "cliche": ("Humanize text", "Text contains formulaic AI phrasing and needs a natural voice."),
    "cb_agenda": (
        "Prepare meeting",
        "Project context needs to become an evidence-grounded, email-ready agenda.",
    ),
    "image_generator": (
        "Create image",
        "You want to create or edit an image from a short description.",
    ),
    "template_builder": (
        "Build template",
        "You need a reusable command template that fits the current project.",
    ),
    "telegram": (
        "Act on source",
        "An accessible source contains a directive you want carried out in context.",
    ),
    "project_personal_growth": (
        "Growth session",
        "You want a guided Personal Growth session and accurate program records.",
    ),
    "finance_review": (
        "Review finances",
        "You want a household money review with clarification and a verified financial PDF.",
    ),
    "project_systems": (
        "Coordinate work",
        "You want to advance the Master Systems Process from its owning files.",
    ),
    "project_decision_helper": (
        "Reason about choice",
        "You want to examine a personal decision while keeping ownership of the choice.",
    ),
    "work_merge": ("Deliver work", "Work needs sanitizing, verification, and safe merge and push."),
    "project_init_llm": (
        "Initialize project",
        "A repository needs AGENTS.md-centered instructions for coding agents.",
    ),
    "pocket_extract": (
        "Extract notes",
        "Pocket ZIP exports need their transcriptions collected with PowerShell.",
    ),
    "tenable_scans": (
        "Extract scans",
        "Scan ZIP files need extraction and consistent naming with PowerShell.",
    ),
    "espansr_help": (
        "Quick reference",
        "You want the static command and CLI reference expanded as text.",
    ),
    "espansr-launcher": ("Open editor", "You want to edit, publish, import, or sync templates."),
    "espansr-commands": (
        "Browse commands",
        "You want to remember the commands and useful combinations available.",
    ),
    "espansr-sync": (
        "Update installation",
        "You want to pull, push local changes, and reinstall this machine.",
    ),
}

for _shell in ("ps", "sh"):
    for _action, _role, _cue in (
        (
            "branch",
            "Create branch",
            "You need to start a branch using the platform's safe Git helper.",
        ),
        (
            "rebase",
            "Update branch",
            "You need to update or rebase work and preserve local changes.",
        ),
        (
            "yolo",
            "Commit & push",
            "You want to commit and push current work using the safe Git helper.",
        ),
    ):
        _CUES[f"git_{_action}_{_shell}"] = (_role, _cue)


def groups_for(entry: CommandCatalogEntry) -> tuple[CommandGroup, ...]:
    """Return overlapping memberships or the explicit custom fallback."""
    return tuple(g for g in COMMAND_GROUPS if entry.capability_id in g.capabilities) or (
        CUSTOM_GROUP,
    )


def command_cue(entry: CommandCatalogEntry) -> tuple[str, str]:
    """Return a compact role and cue, with live guidance for unknown commands."""
    return _CUES.get(
        entry.capability_id, (entry.category or entry.source, entry.use_when or entry.description)
    )
