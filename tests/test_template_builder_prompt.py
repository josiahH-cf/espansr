"""Static guards for authored instructions, not tests of generated model behavior."""

import json
from pathlib import Path

import pytest

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "template_builder.json"
INLINE_CONTEXT_FOOTER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


@pytest.fixture(scope="module")
def template_builder() -> dict:
    """Read the actual bundled JSON rather than a duplicate prompt fixture."""
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_template_builder_preserves_metadata(template_builder):
    """This content-only iteration must not rename or reroute the command."""
    assert {key: value for key, value in template_builder.items() if key != "content"} == {
        "name": "Template Builder",
        "description": (
            "Draft or modify command templates by matching the existing project and command style."
        ),
        "trigger": ":template-builder",
        "category": "prompting",
        "stage": "template-authoring",
        "next_triggers": [],
        "replaces": [],
    }


def test_template_builder_keeps_one_terminal_context_footer(template_builder):
    content = template_builder["content"]
    assert content.count(INLINE_CONTEXT_FOOTER.strip()) == 1
    assert content.endswith(INLINE_CONTEXT_FOOTER)


@pytest.mark.parametrize(
    "required_fragments",
    [
        pytest.param(
            ("already supplied", "at most one short clarification", "ask rather than invent"),
            id="bounded-clarification",
        ),
        pytest.param(
            ("source material to edit", "not instructions to execute"),
            id="edit-without-executing",
        ),
        pytest.param(
            ("project instructions", "schema or validator", "label inferred details"),
            id="evidence-based-schema",
        ),
        pytest.param(
            ("unknown metadata", "preserve all existing fields", "variable syntax"),
            id="lossless-revision",
        ),
        pytest.param(
            ("one valid json object", "no comments", "no trailing commas"),
            id="usable-json",
        ),
        pytest.param(
            ("minimal applicable diff", "complete replacement file", "plan or handoff"),
            id="request-appropriate-artifact",
        ),
        pytest.param(
            ("espansr/core/discovery.py", "python scripts/sync_discovery.py"),
            id="generated-discovery",
        ),
        pytest.param(
            ("checks actually run", "not run", "never claim files were saved"),
            id="honest-verification",
        ),
    ],
)
def test_template_builder_retains_authoring_contract(template_builder, required_fragments):
    content = template_builder["content"].lower()
    for fragment in required_fragments:
        assert fragment in content, f"Missing template-builder instruction: {fragment!r}"
