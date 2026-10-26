"""Qualify prompt delivery and sample structure, not arbitrary model compliance.

The checked-in examples are authored illustrations. The synthetic CLI is run
locally to bind their current-state claims; no receiving model is launched.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from espansr.core.capability_catalog import build_catalog
from espansr.core.command_catalog import build_command_catalog
from espansr.core.command_groups import CUSTOM_GROUP, command_cue, groups_for
from espansr.core.config import Config
from espansr.core.discovery import prompt_note_triggers, render_docs_note_list, render_quick_help
from espansr.core.output_contract import check_output
from espansr.core.recommend import RecommendationQuery, recommend
from espansr.core.templates import Template, TemplateManager
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PROMPTS = (
    ("sample", ":sample", "final-state-sample", "sample_final_state.md"),
    ("user_journey", ":user-journey", "user-journey-specs", "user_journey_specs.md"),
)


@pytest.fixture(params=PROMPTS, ids=[p[0] for p in PROMPTS])
def prompt(request):
    stem, trigger, capability, example = request.param
    data = json.loads((ROOT / "templates" / f"{stem}.json").read_text(encoding="utf-8"))
    return data, trigger, capability, FIXTURES / example


def test_prompt_validates_and_renders_without_a_prerequisite(prompt):
    data, trigger, capability, _ = prompt
    template = Template.from_dict(data)
    assert template.trigger == trigger
    assert template.capability_id == capability
    assert template.variables == []
    assert template.next_triggers == []
    assert validate_template(template) == []
    assert template.render({}) == data["content"]
    assert template.content.endswith("USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n")


def test_prompt_reaches_every_discovery_surface_and_prompt_only_catalog(prompt):
    _, trigger, capability, _ = prompt
    assert prompt_note_triggers().count(trigger) == 1
    assert any(line.strip().startswith(f"{trigger} ") for line in render_quick_help().splitlines())
    assert f"`{trigger}`" in render_docs_note_list()
    catalog = build_catalog(ROOT / "templates")
    assert catalog["validation"] == "passed"
    descriptor = next(e for e in catalog["entries"] if e.get("capability_id") == capability)
    assert descriptor["execution"]["classification"] == "prompt-only"
    entries = build_command_catalog(TemplateManager(templates_dir=ROOT / "templates"), Config())
    entry = next(e for e in entries if e.trigger == trigger)
    assert CUSTOM_GROUP not in groups_for(entry)
    assert command_cue(entry)[1]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("final state projection", ":sample"),
        ("show what would be made if built", ":sample"),
        ("document the backend and build final state specifications", ":user-journey"),
    ],
)
def test_intent_search_finds_the_distinct_authoring_job(query, expected):
    entries = build_command_catalog(TemplateManager(templates_dir=ROOT / "templates"), Config())
    results = recommend(entries, RecommendationQuery(text=query))
    assert results[0].entry.trigger == expected


def test_prompt_copy_and_scratchpad_receive_complete_authoring_instructions(prompt, qtbot):
    from espansr.core.workflows import WorkflowCatalog
    from espansr.ui.commands_popup import CommandsPopupDialog

    data, trigger, _, _ = prompt
    entries = build_command_catalog(TemplateManager(templates_dir=ROOT / "templates"), Config())
    entry = next(e for e in entries if e.trigger == trigger)
    with (
        patch("espansr.ui.commands_popup.get_config", return_value=Config()),
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
        patch("espansr.ui.commands_popup.copy_text") as copy,
    ):
        dialog = CommandsPopupDialog(entries=entries, workflow_catalog=WorkflowCatalog())
        qtbot.addWidget(dialog)
        dialog._search_edit.setText(trigger)
        assert entry in dialog._shown_entries
        dialog._copy_prompt(entry)
        assert copy.call_args.args[0] == data["content"]
        dialog._send_to_scratchpad(entry)
        assert dialog._scratchpad.toPlainText() == data["content"]


def test_example_passes_existing_cli_contract_checker(prompt, capsys):
    from espansr.__main__ import cmd_check_output

    _, trigger, _, example = prompt
    args = argparse.Namespace(template=trigger, path=str(example), json=False)
    with patch("espansr.__main__.get_templates_dir", return_value=ROOT / "templates"):
        assert cmd_check_output(args) == 0
    assert "structural conformance only" in capsys.readouterr().out


def test_contract_reports_each_missing_section(prompt):
    data, _, _, example = prompt
    text = example.read_text(encoding="utf-8")
    contract = data["output_contract"]
    for section in contract["required_sections"]:
        report = check_output(contract, text.replace(f"## {section}\n", ""))
        assert not report.passed
        assert any(section in failure.message for failure in report.failures)


def test_sample_contract_requires_projection_label():
    data = json.loads((ROOT / "templates" / "sample.json").read_text(encoding="utf-8"))
    text = (FIXTURES / "sample_final_state.md").read_text(encoding="utf-8")
    assert not check_output(data["output_contract"], text.replace("PROJECTED", "")).passed


def test_local_journey_example_records_the_actual_gap_without_implementing_it():
    notes = [
        {"title": "Moon", "read": False},
        {"title": "Sea", "read": True},
        {"title": "Forest", "read": False},
    ]
    source = FIXTURES / "journey_notes.py"
    before = source.read_bytes()
    input_text = json.dumps(notes)
    result = subprocess.run(
        [sys.executable, str(source), input_text],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    observed = json.loads(result.stdout)
    expected = ["Moon", "Forest"]
    assert observed == ["Moon", "Sea", "Forest"]
    assert observed != expected  # The authored spec must retain this demonstrated gap.
    assert json.dumps(notes) == input_text
    assert source.read_bytes() == before
    for name in ("sample_final_state.md", "user_journey_specs.md"):
        text = (FIXTURES / name).read_text(encoding="utf-8")
        assert json.dumps(observed) in text
        assert json.dumps(expected) in text


def test_observed_journey_keeps_its_existing_job():
    data = json.loads((ROOT / "templates" / "observed_journey.json").read_text(encoding="utf-8"))
    assert data["trigger"] == ":journey"
    assert data["capability_id"] == "observed-journey"
    assert data["produces"] == ["verification-report"]
