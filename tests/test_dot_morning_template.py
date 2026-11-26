"""Contract for the existing Dot Morning Review expansion."""

import json
from pathlib import Path


def test_dot_morning_opens_day_owner_before_dispatch_and_uses_current_project_context():
    template_path = Path(__file__).resolve().parents[1] / "templates" / "dot_morning.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    prompt = template["content"]
    read, launch = prompt.split("## Start and follow suitable work", maxsplit=1)

    assert template["trigger"] == ":dot-morning"
    assert template["capability_id"] == "dot-morning-review"
    assert "Use `oa_day_review` with `mode: open`" in read
    assert "A rundown alone ends after the read" in read
    assert "review ID and frame" in read
    assert "For each relevant Project" in read
    assert "Keep personal check-in answers with their private cloud owner" in read

    assert "Resolve the exact Project and task from the conversation and current records" in launch
    assert launch.index("fresh `oa_read_context` read") < launch.index(
        "Use the existing selection and launch owners"
    )
    assert "reconcile the original operation before retrying" in launch
    assert "preserve every Stop" in launch
    assert prompt.endswith("USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n")
