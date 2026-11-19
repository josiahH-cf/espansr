"""Contract for the public CB Sync expansion."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cb_sync_is_public_safe_and_review_gated():
    data = json.loads((ROOT / "templates" / "cb_sync.json").read_text(encoding="utf-8"))
    assert data["trigger"] == ":cb-sync"
    assert data["category"] == "analysis"
    content = data["content"]
    assert not re.search(r"https?://|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", content)
    assert "occurrence key and the source file" in content
    assert "Do not create duplicate" in content
    assert content.index("Wait for explicit approval") < content.index("Apply only")
    assert "re-read the affected rows" in content
    assert "Read back the changed rows" in content
    assert "paste-ready rows and say nothing was applied" in content
    assert content.endswith("USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n")
