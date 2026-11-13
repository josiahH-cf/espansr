"""Keep the approved Article Dive directive verbatim and discoverable."""

import hashlib
import json
from pathlib import Path

from espansr.core.command_groups import COMMAND_GROUPS
from espansr.core.discovery import render_docs_note_list, render_quick_help

ROOT = Path(__file__).resolve().parents[1]


def test_article_dive_is_verbatim_and_discoverable():
    note = json.loads((ROOT / "templates/article_dive.json").read_text(encoding="utf-8"))
    assert note["trigger"] == ":article-dive"
    assert note["capability_id"] == "article-dive"
    assert hashlib.sha256(note["content"].encode("utf-8")).hexdigest() == (
        "494dad8d513c26caa3773fe6f848123974bfb3920a669f9cddb02844f1bbd426"
    )
    assert ":article-dive" in render_quick_help()
    assert "`:article-dive`" in render_docs_note_list()
    assert [g.id for g in COMMAND_GROUPS if "article-dive" in g.capabilities] == [
        "research-challenge"
    ]
