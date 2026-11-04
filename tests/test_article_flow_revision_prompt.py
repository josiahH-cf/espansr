"""Contract for :article-flow-revision, Article Flow's revision entry prompt.

Article Flow's owner supplied the prompt text; espansr bundles it verbatim and
owns only its registration. Expanding the trigger inserts the prompt and
nothing else: it starts no Article Flow run and publishes nothing.
"""

import hashlib
import json
from pathlib import Path

import pytest

from espansr.core.command_groups import COMMAND_GROUPS
from espansr.core.discovery import SYSTEM_TRIGGERS, render_docs_note_list, render_quick_help

ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "templates" / "article_flow_revision.json"
# sha256 of the prompt text exactly as Article Flow's owner handed it over.
SUPPLIED_SHA256 = "0214c913f364a75f000796516f2b11050d0b797835213d64a5ac749904952ff6"


def _note() -> dict:
    return json.loads(NOTE.read_text(encoding="utf-8"))


def _prose(text: str) -> str:
    return " ".join(text.split())


def test_the_prompt_is_the_supplied_text_byte_for_byte():
    content = _note()["content"]
    assert hashlib.sha256(content.encode("utf-8")).hexdigest() == SUPPLIED_SHA256


def test_it_is_a_shareable_bundled_note_with_its_own_trigger():
    note = _note()
    assert note["trigger"] == ":article-flow-revision"
    assert "local_only" not in note
    assert note["capability_id"] == "article-flow-revision"
    triggers = {
        json.loads(path.read_text(encoding="utf-8"))["trigger"]
        for path in (ROOT / "templates").glob("*.json")
    } | set(SYSTEM_TRIGGERS)
    clashing = [t for t in triggers - {note["trigger"]} if t.startswith(note["trigger"])]
    shadowing = [t for t in triggers - {note["trigger"]} if note["trigger"].startswith(t)]
    assert (clashing, shadowing) == ([], [])


def test_it_is_discoverable_in_help_docs_and_its_group():
    assert ":article-flow-revision" in render_quick_help()
    assert "`:article-flow-revision`" in render_docs_note_list()
    groups = [g.id for g in COMMAND_GROUPS if "article-flow-revision" in g.capabilities]
    assert groups == ["explain-communicate"]


@pytest.mark.parametrize(
    "promise",
    [
        # The article is read and confirmed before anything is edited.
        "Before editing, confirm that you found and read it by giving its title, canonical link "
        "and original publication date",
        "say exactly what is missing instead of guessing",
        # Source identity is never invented; the export pair is the fallback.
        "Keep the complete JSON unchanged as source.json",
        "use the matching Article Flow revision-export source.json and article.md when supplied",
        "Never invent source identity or calculate a hash from browser-rendered text.",
        # The author's words stay theirs.
        "invite me to give it in my own words",
        "Keep my exact feedback separate from your proposed article.",
        # The three files the import takes, and the stop on a failed check.
        "Return three separate UTF-8 files: source.json unchanged, candidate.md with the complete "
        "revised Markdown, and feedback.md with my exact feedback.",
        "Failed checks or material conflicts must retain my candidate and stop for resolution",
    ],
)
def test_the_prompt_keeps_the_contract_article_flow_imports(promise):
    assert promise in _prose(_note()["content"])
