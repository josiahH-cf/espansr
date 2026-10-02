"""Output-contract acceptance checks (ARCH-07, BEH-10).

Output contracts are optional machine-readable structural obligations on
model-generated responses. The checker reports every missing obligation,
exits nonzero on failure, distinguishes parse failure / missing contract /
failed contract / passing contract, and never claims semantic correctness.
"""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from espansr.core.output_contract import check_output, normalize_contract

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"

SIMPLE_CONTRACT = {
    "schema": 1,
    "required_sections": ["RESULT", "EVIDENCE"],
    "required_markers": [
        {"pattern": "Verdict:", "min_count": 2, "message": "two verdicts required"},
        {"pattern": "STATUS:\\s*(GREEN|RED)", "regex": True, "min_count": 1, "max_count": 1},
    ],
    "forbidden_markers": [
        {"pattern": "TODO", "message": "unresolved TODO left in output"},
    ],
}

PASSING_OUTPUT = """RESULT

All good.

EVIDENCE

Verdict: ok
Verdict: ok
STATUS: GREEN
"""


def _litmus_entries(count, human_verdict_blank=True):
    human = (
        "Human verdict: PASS | FAIL - why:"
        if human_verdict_blank
        else "Human verdict: PASS - why: looks fine to me"
    )
    return "\n\n".join(
        f"### Observable change {i}\n\n"
        f"**If this was built correctly:** A person does the thing and sees result {i}.\n\n"
        f"- Model verdict: PASS | FAIL - why: <filled after implementation verification>\n"
        f"- {human}"
        for i in range(1, count + 1)
    )


HUMAN_VERDICT_CONTRACT = {
    "schema": 1,
    "required_markers": [{"pattern": "Human verdict:", "min_count": 1}],
    "forbidden_markers": [
        {"pattern": r"Human verdict:\s*PASS(?!\s*\|)", "regex": True},
        {"pattern": r"Human verdict:\s*FAIL", "regex": True},
    ],
}


def _review_output():
    return """ADVERSARY REVIEW
VERDICT: PASS

SCOPE REVIEWED
The documentation change and its stated requirements.

STABILITY
Inspected the changed references and checked the documented command.
"""


# ── Core checker semantics ───────────────────────────────────────────────────


def test_passing_output_reports_no_failures():
    report = check_output(SIMPLE_CONTRACT, PASSING_OUTPUT)
    assert report.passed
    assert report.failures == []


def test_every_missing_obligation_is_reported_not_only_the_first():
    report = check_output(SIMPLE_CONTRACT, "TODO nothing here Verdict: once")
    assert not report.passed
    messages = "\n".join(f.message for f in report.failures)
    assert "RESULT" in messages
    assert "EVIDENCE" in messages
    assert "two verdicts required" in messages
    assert "STATUS" in messages
    assert "TODO" in messages
    assert len(report.failures) >= 5


def test_marker_max_count_is_enforced():
    doubled = PASSING_OUTPUT + "\nSTATUS: RED\n"
    report = check_output(SIMPLE_CONTRACT, doubled)
    assert not report.passed
    assert any("STATUS" in f.message for f in report.failures)


def test_structural_pass_never_claims_semantic_correctness():
    report = check_output(SIMPLE_CONTRACT, PASSING_OUTPUT)
    summary = report.summary()
    assert "structural" in summary.lower()
    assert "semantic" in summary.lower()


def test_normalize_contract_rejects_non_contracts():
    assert normalize_contract(None) is None
    assert normalize_contract("nope") is None
    assert normalize_contract({}) is None
    assert normalize_contract({"schema": 1, "required_sections": ["A"]}) is not None


def test_malformed_marker_entries_are_skipped_conservatively():
    contract = {
        "schema": 1,
        "required_sections": ["RESULT"],
        "required_markers": ["not-a-dict", {"no_pattern": True}],
    }
    report = check_output(contract, "RESULT\nok")
    assert report.passed


# ── Bundled adaptive contracts and regex semantics ───────────────────────────


def _review_contract():
    data = json.loads((TEMPLATES_DIR / "adversary_review.json").read_text(encoding="utf-8"))
    contract = normalize_contract(data.get("output_contract"))
    assert contract is not None
    return contract


def test_review_contract_passes_without_empty_finding_categories():
    report = check_output(_review_contract(), _review_output())
    assert report.passed, [f.message for f in report.failures]
    assert "OPTIONAL" not in _review_contract()["required_sections"]


def test_review_contract_requires_scope_verification_and_one_verdict():
    report = check_output(_review_contract(), "ADVERSARY REVIEW")
    assert not report.passed
    messages = "\n".join(f.message for f in report.failures)
    for obligation in ("SCOPE REVIEWED", "STABILITY", "VERDICT"):
        assert obligation in messages
    assert not check_output(_review_contract(), _review_output() + "\nVERDICT: FAIL").passed


def test_adaptive_feature_does_not_declare_fixed_format_contract():
    data = json.loads((TEMPLATES_DIR / "feature.json").read_text(encoding="utf-8"))
    assert normalize_contract(data.get("output_contract")) is None


def test_regex_forbids_prefilled_pass_human_verdict():
    report = check_output(HUMAN_VERDICT_CONTRACT, _litmus_entries(1, human_verdict_blank=False))
    assert not report.passed


def test_regex_forbids_prefilled_fail_human_verdict():
    output = _litmus_entries(1).replace(
        "Human verdict: PASS | FAIL - why:", "Human verdict: FAIL - why: broken"
    )
    assert not check_output(HUMAN_VERDICT_CONTRACT, output).passed


def test_blank_human_verdict_template_line_is_not_a_false_positive():
    """A PASS | FAIL template must not be mistaken for fabricated acceptance."""
    assert check_output(HUMAN_VERDICT_CONTRACT, _litmus_entries(3)).passed


# ── CLI: espansr check-output ────────────────────────────────────────────────


def _run_check_output(tmp_path, output_text, template=":adversary-review", templates_dir=None):
    from espansr.__main__ import cmd_check_output

    out_file = tmp_path / "output.txt"
    out_file.write_text(output_text, encoding="utf-8")
    args = argparse.Namespace(template=template, path=str(out_file), json=False)
    with patch(
        "espansr.__main__.get_templates_dir",
        return_value=templates_dir if templates_dir is not None else TEMPLATES_DIR,
    ):
        return cmd_check_output(args)


def test_cli_check_output_passes_on_conforming_output(tmp_path, capsys):
    assert _run_check_output(tmp_path, _review_output()) == 0
    out = capsys.readouterr().out
    assert "pass" in out.lower()


def test_cli_check_output_fails_nonzero_and_reports_all(tmp_path, capsys):
    bad = "ADVERSARY REVIEW"
    assert _run_check_output(tmp_path, bad) == 1
    out = capsys.readouterr().out
    assert "SCOPE REVIEWED" in out
    assert "STABILITY" in out
    assert "VERDICT" in out


def test_cli_check_output_distinguishes_missing_contract(tmp_path, capsys):
    plain_dir = tmp_path / "plain-templates"
    plain_dir.mkdir()
    (plain_dir / "plain.json").write_text(
        json.dumps({"name": "Plain", "content": "x", "trigger": ":plain"}), encoding="utf-8"
    )
    rc = _run_check_output(tmp_path, "anything", template=":plain", templates_dir=plain_dir)
    assert rc == 2
    assert "no output contract" in capsys.readouterr().out.lower()


def test_cli_check_output_distinguishes_unknown_template(tmp_path, capsys):
    empty_dir = tmp_path / "empty-templates"
    empty_dir.mkdir()
    rc = _run_check_output(tmp_path, "anything", template=":ghost", templates_dir=empty_dir)
    assert rc == 3
    assert "not found" in capsys.readouterr().out.lower()


def test_cli_check_output_distinguishes_unreadable_output_file(tmp_path, capsys):
    from espansr.__main__ import cmd_check_output

    args = argparse.Namespace(
        template=":adversary-review", path=str(tmp_path / "missing.txt"), json=False
    )
    with patch("espansr.__main__.get_templates_dir", return_value=TEMPLATES_DIR):
        rc = cmd_check_output(args)
    assert rc == 3
    assert "cannot read" in capsys.readouterr().out.lower()


def test_cli_check_output_is_read_only(tmp_path):
    """Validation never mutates the output file or the template store."""
    out_file = tmp_path / "output.txt"
    out_file.write_text(_review_output(), encoding="utf-8")
    before = out_file.read_text(encoding="utf-8")
    review_before = (TEMPLATES_DIR / "adversary_review.json").read_text(encoding="utf-8")

    from espansr.__main__ import cmd_check_output

    args = argparse.Namespace(template=":adversary-review", path=str(out_file), json=False)
    with patch("espansr.__main__.get_templates_dir", return_value=TEMPLATES_DIR):
        cmd_check_output(args)

    assert out_file.read_text(encoding="utf-8") == before
    assert (TEMPLATES_DIR / "adversary_review.json").read_text(encoding="utf-8") == review_before


def test_cli_adaptive_feature_reports_missing_contract_not_success(tmp_path, capsys):
    rc = _run_check_output(tmp_path, "A native specification", template=":feature")
    assert rc == 2
    assert "no output contract" in capsys.readouterr().out.lower()
