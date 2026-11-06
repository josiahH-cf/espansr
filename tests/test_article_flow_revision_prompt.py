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
SUPPLIED_SHA256 = "98fd36eeff955b1398c1e96e57f8b8d9e1f752d9ecd6e13813dbe2c003986bc1"


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
        "First contextualize; do not edit yet.",
        "I should not have to upload or paste source.json or article.md.",
        "retain the COMPLETE retrieved JSON, unchanged",
        "Add a fresh unique ?article-flow=REQUEST_TAG",
        "Never invent identity fields, calculate source hashes from browser-rendered text",
        "Keep my actual feedback separate from generated text.",
        "Use a semantic visual_plan for any new or replaced diagram",
        "An arrow exists only when you supply it",
        "create and return a downloadable ZIP file",
        "Include revision-bundle.json",
        "Include INGESTION.txt and return its text below the ZIP download",
        "Put all files at the ZIP root.",
        '"article_flow_bundle_version":"1.0.0"',
        '"candidate_file":"SLUG.revised.md"',
        '"author_feedback_file":"author-feedback.txt"',
        "The backend unpacks it, validates it, and automatically republishes "
        "within my revision authorization.",
        "Failed checks retain the candidate for resolution rather than silently rewriting it.",
    ],
)
def test_the_prompt_keeps_the_contract_article_flow_imports(promise):
    assert promise in _prose(_note()["content"])


def test_the_first_reply_asks_for_thoughts_and_waits_before_drafting():
    content = _prose(_note()["content"])
    first_reply = content.split("For your first reply,", 1)[1]
    assert first_reply.index("after contextualization") < first_reply.index(
        "confirm you have everything"
    )
    assert first_reply.index("then ask for my thoughts") < first_reply.index(
        "Stop and wait for my reply"
    )
    assert first_reply.endswith("before drafting or producing the ZIP.")
    assert "Return three separate UTF-8 files" not in content
