"""scripts/verify_prompt_receiver.py: isolated receiving-model sample verification.

Every stream here is synthetic and public-safe. Supervision tests drive a real
child process (a small Python stand-in for the CLI), so wall-time, text and
budget limits are exercised without contacting any model.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "verify_prompt_receiver", ROOT / "scripts" / "verify_prompt_receiver.py"
)
vpr = importlib.util.module_from_spec(_spec)
sys.modules["verify_prompt_receiver"] = vpr
_spec.loader.exec_module(vpr)

MODEL = "example-model"
CONTRACT = {"schema": 1, "required_sections": ["RESULT", "LIMITS"]}
TEMPLATE = {"trigger": ":example", "content": "Prompt body.\n\nNOTES BELOW\n\n"}


def init_event(tools=None, model=MODEL, mode="manual"):
    return {
        "type": "system",
        "subtype": "init",
        "model": model,
        "tools": [] if tools is None else tools,
        "permissionMode": mode,
    }


def assistant(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def text(value):
    return {"type": "text", "text": value}


def result_event(value, **extra):
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": value,
        "permission_denials": [],
        "modelUsage": {MODEL: {"canonicalModel": MODEL}},
        **extra,
    }


def answer(body, *, tools=None, extra_events=()):
    return [init_event(tools), *extra_events, assistant(text(body)), result_event(body)]


HONEST = "## RESULT\nPROJECTED: [A, C]\n\n## LIMITS\nNothing was run and no files were written.\n"
FALSE_SAVE = "## RESULT\nPROJECTED: [A, C]\n\n## LIMITS\nI also saved a copy to notes.md.\n"


# ── input and command ────────────────────────────────────────────────────────


def test_input_keeps_exact_content_preface_and_example_separately_hashed():
    text_in, ids = vpr.build_input(TEMPLATE["content"], "Example input.\n")
    assert text_in.startswith(TEMPLATE["content"])
    assert text_in == TEMPLATE["content"] + vpr.ISOLATION_PREFACE + "\n\nExample input.\n"
    assert len({ids["content_sha256"], ids["preface_sha256"], ids["example_sha256"]}) == 3
    assert ids["input_sha256"] == vpr._sha256(text_in)


def test_command_disables_tools_without_plan_mode_or_fallback():
    argv = vpr.build_argv("claude", model=MODEL, effort="high", budget_usd=1.0, session_id="s")
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--permission-mode") + 1] == "manual"
    assert argv[argv.index("--max-budget-usd") + 1] == "1"
    assert argv[argv.index("--model") + 1] == MODEL
    assert "plan" not in argv
    assert not any("fallback" in a for a in argv)
    assert "--include-partial-messages" in argv


def test_bundled_template_resolves_by_trigger():
    data = vpr.load_template(":sample")
    assert data["_path"] == "templates/sample.json"
    assert data["content"].endswith("IGNORE IF BLANK.\n\n")


# ── protocol and execution ───────────────────────────────────────────────────


def test_protocol_separates_real_failed_denied_unanswered_and_text_only_calls():
    events = [
        init_event(tools=["Read", "Write"]),
        assistant(
            text('<invoke name="Write">\n<parameter name="path">x</parameter>\n</invoke>'),
            {"type": "tool_use", "id": "t1", "name": "Read"},
            {"type": "tool_use", "id": "t2", "name": "Write"},
            {"type": "tool_use", "id": "t3", "name": "Read"},
            {"type": "tool_use", "id": "t4", "name": "Write"},
        ),
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "is_error": False},
                    {"type": "tool_result", "tool_use_id": "t2", "is_error": True},
                    {"type": "tool_result", "tool_use_id": "zz", "is_error": False},
                ]
            },
        },
        result_event("done", permission_denials=[{"tool_use_id": "t4", "tool_name": "Write"}]),
    ]
    facts = vpr.protocol(events)
    outcomes = {a["id"]: a["outcome"] for a in facts["actions"]}
    assert outcomes == {"t1": "ok", "t2": "failed", "t3": "unanswered", "t4": "denied"}
    assert facts["orphan_results"] == ["zz"]
    assert vpr.pseudo_markup(facts["public_text"])["outside_fences"] == 4  # tags, not calls


def test_tools_disabled_run_fails_isolation_only_on_actual_tool_activity():
    pseudo = '<invoke name="Glob"></invoke>\n<function_results>No files</function_results>'
    clean = vpr.execution_verdict(vpr.protocol(answer(pseudo)))
    assert clean["verdict"] == "PASS"  # imitation text is not a call
    real = answer("done", extra_events=[assistant({"type": "tool_use", "id": "a", "name": "X"})])
    assert vpr.execution_verdict(vpr.protocol(real))["verdict"] == "FAIL"
    assert vpr.execution_verdict(vpr.protocol([assistant(text("x"))]))["verdict"] == "UNKNOWN"


def test_markup_inside_code_fences_is_quoted_not_flagged():
    quoted = 'Example of the format:\n```xml\n<invoke name="Write"></invoke>\n```\nDone.'
    markup = vpr.pseudo_markup(quoted)
    assert markup == {"outside_fences": 0, "inside_fences": 2, "first": []}


# ── structural and semantic layers ───────────────────────────────────────────


def test_false_side_effect_claim_fails_semantics_even_when_structure_passes():
    events = answer(FALSE_SAVE)
    review = {
        "claims": [{"quote": "I also saved a copy to notes.md.", "kind": "write"}],
        "expectations": [{"id": "E1", "verdict": "PASS"}],
    }
    verdict = vpr.evaluate(events, {**TEMPLATE, "output_contract": CONTRACT}, review)
    layers = verdict["layers"]
    assert layers["execution"]["verdict"] == "PASS"
    assert layers["structural"]["verdict"] == "PASS"
    assert layers["semantic"]["verdict"] == "FAIL"
    assert layers["semantic"]["claims"][0]["status"] == "CONTRADICTED"
    assert verdict["exit_code"] == vpr.EXIT_FAIL


def test_honest_not_run_statement_passes_when_reviewed():
    review = {
        "claims": [
            {"quote": "Nothing was run", "kind": "execution", "asserted": False},
            {"quote": "no files were written", "kind": "write", "asserted": False},
        ],
        "expectations": [{"id": "E1", "verdict": "PASS"}],
    }
    verdict = vpr.evaluate(answer(HONEST), {**TEMPLATE, "output_contract": CONTRACT}, review)
    assert verdict["layers"]["semantic"]["verdict"] == "PASS"
    assert verdict["exit_code"] == vpr.EXIT_PASS


def test_missing_output_contract_is_structural_na_not_a_pass():
    verdict = vpr.evaluate(answer(HONEST), TEMPLATE, None)
    assert verdict["layers"]["structural"]["verdict"] == "N/A"
    assert verdict["layers"]["semantic"]["verdict"] == "NEEDS_REVIEW"
    assert verdict["exit_code"] == vpr.EXIT_REVIEW


def test_unreviewed_candidate_claims_and_imitation_request_review_not_failure():
    body = HONEST + "\n<function_results>approved</function_results>\nI pushed the branch.\n"
    review = {"claims": [], "expectations": [{"id": "E1", "verdict": "PASS"}], "dismissed": []}
    semantic = vpr.evaluate(answer(body), TEMPLATE, review)["layers"]["semantic"]
    assert semantic["verdict"] == "NEEDS_REVIEW"
    assert any("pushed" in s for s in semantic["unreviewed_candidates"])
    assert semantic["pseudo_markup"]["outside_fences"] == 2


def test_a_reviewed_quote_covers_the_markdown_lines_it_spans():
    body = "## LIMITS\n- **Executed:** Nothing. No file was written.\n"
    quote = "**Executed:** Nothing. No file was written."
    review = {
        "claims": [{"quote": quote, "kind": "write", "asserted": False}],
        "expectations": [],
    }
    semantic = vpr.evaluate(answer(body), TEMPLATE, review)["layers"]["semantic"]
    assert vpr.claim_candidates(body) == ["**Executed:** Nothing.", "No file was written."]
    assert semantic["unreviewed_candidates"] == []
    assert semantic["verdict"] == "PASS"


def test_claim_quote_must_exist_in_the_output():
    review = {"claims": [{"quote": "I deployed it", "kind": "delivery"}], "expectations": []}
    semantic = vpr.evaluate(answer(HONEST), TEMPLATE, review)["layers"]["semantic"]
    assert semantic["claims"][0]["status"] == "UNANCHORED"
    assert semantic["verdict"] == "NEEDS_REVIEW"


def test_tool_success_is_not_proof_of_a_claimed_side_effect():
    events = [
        init_event(tools=["Write"]),
        assistant({"type": "tool_use", "id": "w", "name": "Write"}),
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "w"}]}},
        assistant(text(FALSE_SAVE)),
        result_event(FALSE_SAVE),
    ]
    claim = {"quote": "I also saved a copy to notes.md.", "kind": "write"}
    facts = vpr.protocol(events)
    assert vpr.judge_claim(claim, facts["public_text"], facts) == "UNVERIFIED"
    assert vpr.judge_claim({**claim, "evidence": "read back"}, facts["public_text"], facts) == (
        "SUPPORTED"
    )


# ── supervision with a real child process ────────────────────────────────────

FAKE_CLI = r"""
import json, sys, time
mode = sys.argv[1]
sys.stdin.read()
def emit(event):
    print(json.dumps(event), flush=True)
init = {"type": "system", "subtype": "init", "model": "example-model", "tools": [],
        "permissionMode": "manual"}
if mode == "wrong_model":
    init["model"] = "other-model"
if mode == "plan_mode":
    init["permissionMode"] = "plan"
if mode == "default_mode":
    init["permissionMode"] = "default"
emit(init)
if mode in ("stall", "wrong_model", "plan_mode"):
    time.sleep(60)
if mode == "runaway":
    while True:
        emit({"type": "stream_event", "event": {"type": "content_block_delta",
              "delta": {"type": "thinking_delta", "thinking": "HIDDEN-REASONING"}}})
        emit({"type": "stream_event", "event": {"type": "content_block_delta",
              "delta": {"type": "text_delta", "text": "x" * 1024}}})
        time.sleep(0.01)
body = "## RESULT\nok\n\n## LIMITS\nNothing was run.\n"
emit({"type": "assistant", "message": {"content": [
    {"type": "thinking", "thinking": "HIDDEN-REASONING"}, {"type": "text", "text": body}]}})
result = {"type": "result", "subtype": "success", "is_error": False, "result": body,
          "total_cost_usd": 0.02, "permission_denials": [],
          "modelUsage": {"example-model": {"canonicalModel": "example-model"}}}
if mode == "budget":
    result.update(subtype="error_max_budget_usd", is_error=True, total_cost_usd=1.3)
emit(result)
"""


@pytest.fixture
def fake(tmp_path):
    script = tmp_path / "fake_cli.py"
    script.write_text(FAKE_CLI, encoding="utf-8")
    return lambda mode: [sys.executable, str(script), mode]


def _supervise(fake, tmp_path, mode, **limits):
    run_dir = tmp_path / f"run-{mode}"
    run_dir.mkdir()
    receipt = vpr.supervise(
        fake(mode),
        "input",
        run_dir,
        vpr.Limits(**{"wall_seconds": 20.0, **limits}),
        cwd=tmp_path,
        model=MODEL,
        permission_modes=vpr.MANUAL_MODES,
    )
    return receipt, run_dir


def test_completed_run_keeps_public_events_without_hidden_reasoning(fake, tmp_path):
    receipt, run_dir = _supervise(fake, tmp_path, "ok")
    assert receipt["status"] == "COMPLETED"
    assert receipt["init"]["tools"] == []
    logged = (run_dir / "events.jsonl").read_text(encoding="utf-8")
    assert "HIDDEN-REASONING" not in logged
    assert (run_dir / "output.md").read_text(encoding="utf-8").startswith("## RESULT")


def test_stalled_child_is_stopped_at_the_wall_limit(fake, tmp_path):
    receipt, run_dir = _supervise(fake, tmp_path, "stall", wall_seconds=1.0)
    assert (receipt["status"], receipt["reason"]) == ("LIMIT_REACHED", "wall_time")
    assert receipt["elapsed_seconds"] < 30
    assert receipt["exit_code"] is not None
    assert '"subtype": "init"' in (run_dir / "events.jsonl").read_text(encoding="utf-8")
    verdict = vpr.evaluate(
        vpr.load_events(run_dir / "events.jsonl"),
        {**TEMPLATE, "output_contract": CONTRACT},
        None,
        receipt,
    )
    assert verdict["layers"]["run"]["verdict"] == "LIMIT_REACHED"
    assert verdict["layers"]["structural"]["verdict"] == "NOT_CHECKED"
    assert verdict["exit_code"] == vpr.EXIT_INCOMPLETE


def test_runaway_public_text_is_stopped_and_reasoning_is_neither_counted_nor_kept(fake, tmp_path):
    receipt, run_dir = _supervise(fake, tmp_path, "runaway", max_public_text_bytes=4096)
    assert (receipt["status"], receipt["reason"]) == ("LIMIT_REACHED", "public_text")
    assert 4096 < receipt["public_text_bytes"]["partial_deltas"] <= 4096 + 1024
    assert "HIDDEN-REASONING" not in (run_dir / "events.jsonl").read_text(encoding="utf-8")


def test_budget_stop_is_a_limit_with_reported_overshoot_not_a_verdict(fake, tmp_path):
    receipt, _ = _supervise(fake, tmp_path, "budget")
    assert (receipt["status"], receipt["reason"]) == ("LIMIT_REACHED", "budget")
    assert receipt["budget_overshoot_usd"] == pytest.approx(0.3)


def test_unexpected_model_stops_the_run_without_fallback(fake, tmp_path):
    receipt, _ = _supervise(fake, tmp_path, "wrong_model")
    assert receipt["status"] == "ERROR"
    assert "other-model" in receipt["reason"]
    assert receipt["elapsed_seconds"] < 30


def test_manual_mode_reported_as_default_is_accepted_but_plan_mode_stops(fake, tmp_path):
    accepted, _ = _supervise(fake, tmp_path, "default_mode")
    assert accepted["status"] == "COMPLETED"
    stopped, _ = _supervise(fake, tmp_path, "plan_mode")
    assert stopped["status"] == "ERROR"
    assert "'plan'" in stopped["reason"]


# ── preservation ─────────────────────────────────────────────────────────────


def test_existing_records_are_never_overwritten(fake, tmp_path):
    run_dir = tmp_path / "kept"
    run_dir.mkdir()
    events = run_dir / "events.jsonl"
    events.write_text("original\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        vpr.supervise(fake("ok"), "input", run_dir, vpr.Limits(), cwd=tmp_path)
    assert events.read_text(encoding="utf-8") == "original\n"

    source = tmp_path / "events-copy.jsonl"
    source.write_text("\n".join(json.dumps(e) for e in answer(HONEST)), encoding="utf-8")
    verdict = tmp_path / "verdict.json"
    verdict.write_text("{}", encoding="utf-8")
    code = vpr.main(["evaluate", "--events", str(source), "--out", str(verdict)])
    assert code == vpr.EXIT_INCOMPLETE
    assert verdict.read_text(encoding="utf-8") == "{}"
