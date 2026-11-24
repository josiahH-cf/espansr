"""Contract for the public CB Sync expansion."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cb_sync():
    return json.loads((ROOT / "templates" / "cb_sync.json").read_text(encoding="utf-8"))


def test_cb_sync_is_public_safe_and_review_gated(cb_sync):
    assert cb_sync["trigger"] == ":cb-sync"
    assert cb_sync["category"] == "analysis"
    assert not cb_sync.get("variables")
    content = cb_sync["content"]
    assert not re.search(r"https?://|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", content)
    assert "exact native Sheets URL or ID from private context" in content
    assert content.index("Wait for explicit approval") < content.index("Apply only approved")
    assert content.endswith("USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n")


def test_cb_sync_separates_upcoming_agenda_from_completed_meeting_evidence(cb_sync):
    content = cb_sync["content"]
    assert "A transcript is optional" in content
    assert "preserving every approved topic" in content
    assert not re.search(r"up to three|at most three|three agenda items", content, re.I)
    assert "does not confirm a decision or commitment" in content
    assert "selected for the exact completed occurrence" in content
    assert "Hold unsupported or conflicting changes" in content


def test_cb_sync_pins_the_calendar_instance_and_the_managed_block(cb_sync):
    content = cb_sync["content"]
    assert "Monday CB Sync or separate repeating Thursday Sync" in content
    assert "actual start time in America/Chicago" in content
    assert "calendar ID, occurrence event ID, recurring series identity" in content
    assert "expected attendees verified against private context" in content
    assert "Ask if the occurrence, calendar, time, or attendees are ambiguous" in content
    assert "[Cherry Bridge agenda]" in content and "[/Cherry Bridge agenda]" in content
    assert "co-owner's attributable notes verbatim above the block" in content
    assert "Never rewrite or remove unowned text" in content
    assert "patch only the description field" in content


def test_cb_sync_preserves_history_and_reconciles_partial_writes(cb_sync):
    content = cb_sync["content"]
    assert "Reuse IDs on rerun" in content
    assert "Keep an item open when moved off the invite" in content
    assert "Append keyed history entries to Review result" in content
    assert "Preserve the outgoing text for superseded agenda items" in content
    assert "skip an entry whose occurrence, item and revision or change ID already match" in content
    assert content.index("read back superseded confirmed agenda entries") < content.index(
        "patch only the description field"
    )
    assert "Confirm the workbook and invite separately" in content
    assert "re-read both original targets" in content
    assert "paste-ready cells and an invite block" in content
    assert "report success without readback" in content
    assert "unsent email draft" in content
    assert "only the current agenda bullets and the same agenda link" in content
    assert "Exclude history and dropped topics" in content


def test_cb_sync_reconciles_shared_checkpoints_through_dot_review(cb_sync):
    _, _, tail = cb_sync["content"].partition("\n## Reconcile shared checkpoints\n")
    step, _, _ = tail.partition("\nUSER CONTEXT")
    assert step, "expected the separate checkpoint reconciliation step"
    assert "For post-meeting reconciliation only" in step
    assert "confirmed decisions from the selected completed occurrence" in step
    assert "shared Cherry Bridge entrypoints' checkpoints" in step
    assert "proposal ID, class (standing or ask-first), and evidence" in step
    assert "Keep checkpoint proposals separate from the workbook and invite review" in step
    assert "verifying its result or condition outside the meeting notes" in step
    assert "ask-first change only after explicit approval of that proposal ID" in step
    route = "Use only the `changes` operation of `oa_day_review` or `oa_weekly_review` in Dot"
    assert route in step
    assert "Keep each assignee and every existing task ID" in step
    assert "never write an `na-ai` task" in step
    assert "If neither review operation is available or one refuses a change" in step
    assert "return the proposed checkpoint changes and state exactly what was not applied" in step
