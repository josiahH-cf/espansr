"""Capability identity and artifact-type helpers for the process layer.

A *capability* is an independently invocable job represented by a template or
system command. Workflow manifests reference capabilities by stable ID, never
by trigger, so a trigger rename cannot break workflow identity.

Derived-ID policy (deterministic, documented, and tested):

1. An explicit ``capability_id`` on the template wins.
2. A template loaded from disk falls back to its file stem (the on-disk
   identity, which survives trigger renames).
3. An unsaved template falls back to the slug of its name (the same slug its
   file stem would use once saved).
"""

from __future__ import annotations

from espansr.core.templates import Template

# The shared artifact-type vocabulary used by ``accepts``/``produces`` metadata,
# workflow manifests, handoff packets, and the recommendation engine. The list
# is a discovery aid, not a gate: templates may declare additional types.
ARTIFACT_TYPES: tuple[str, ...] = (
    "rough-intent",
    "goal-contract",
    "research-question",
    "evidence-report",
    "gap-review",
    "human-litmus",
    "implementation-handoff",
    "implemented-feature",
    "visual-artifact",
    "interactive-html",
    "verification-report",
    "feedback-directives",
    "context-packet",
)


def effective_capability_id(template: Template) -> str:
    """Return the stable capability ID for *template*.

    Explicit ``capability_id`` first, then the on-disk file stem, then the
    name slug for unsaved templates.
    """
    if template.capability_id:
        return template.capability_id
    if template._path is not None:
        return template._path.stem
    return template.filename[: -len(".json")]
