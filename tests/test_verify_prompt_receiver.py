"""scripts/verify_prompt_receiver.py: isolated receiving-model sample verification.

Every stream here is synthetic and public-safe. Supervision tests drive a real
child process (a small Python stand-in for the CLI), so wall-time, text and
budget limits are exercised without contacting any model.
"""

import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
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


@pytest.mark.parametrize("receipt", [None, {"status": "COMPLETED"}])
@pytest.mark.parametrize(
    "fields, state",
    [
        ({"is_error": True, "subtype": "error_max_budget_usd"}, "LIMIT_REACHED"),
        ({"is_error": True, "subtype": "error_during_execution"}, "ERROR"),
        ({"is_error": True, "subtype": "success"}, "ERROR"),
        ({"is_error": False, "subtype": "error_max_budget_usd"}, "LIMIT_REACHED"),
        ({"is_error": False, "subtype": "error_during_execution"}, "ERROR"),
        ({"is_error": "false"}, "ERROR"),
        ({"is_error": 0}, "ERROR"),
        ({"is_error": None}, "ERROR"),
        ({"subtype": None}, "ERROR"),
        ({"subtype": ["success"]}, "ERROR"),
        ({"subtype": "unknown"}, "ERROR"),
        ({"result": {"text": "ok"}}, "ERROR"),
        ({"errors": ["execution failed"]}, "ERROR"),
        ({"errors": "invalid errors field"}, "ERROR"),
        ({"permission_denials": "invalid denials field"}, "ERROR"),
        ({"permission_denials": [None]}, "ERROR"),
    ],
)
def test_failed_or_malformed_result_cannot_pass_without_a_receipt(fields, state, receipt):
    events = answer("ok")
    events[-1].update(fields)
    verdict = vpr.evaluate(events, TEMPLATE, {"claims": [], "expectations": []}, receipt)
    assert verdict["exit_code"] == vpr.EXIT_INCOMPLETE
    assert verdict["layers"]["run"]["verdict"] == state
    assert verdict["layers"]["run"]["note"]
    assert verdict["layers"]["structural"]["verdict"] == "NOT_CHECKED"


@pytest.mark.parametrize("receipt", [None, {"status": "COMPLETED"}])
def test_valid_result_can_pass_with_or_without_receipt(receipt):
    verdict = vpr.evaluate(answer("ok"), TEMPLATE, {"claims": [], "expectations": []}, receipt)
    assert verdict["exit_code"] == vpr.EXIT_PASS
    assert verdict["layers"]["run"]["verdict"] == (
        "NOT_RECORDED" if receipt is None else "COMPLETED"
    )


@pytest.mark.parametrize("receipt", [None, {"status": "COMPLETED"}])
@pytest.mark.parametrize("missing", ["event", "result", "is_error", "subtype"])
def test_missing_result_or_required_result_field_is_incomplete(receipt, missing):
    events = answer("ok")
    if missing == "event":
        events.pop()
    else:
        events[-1].pop(missing)
    verdict = vpr.evaluate(events, TEMPLATE, {"claims": [], "expectations": []}, receipt)
    assert verdict["exit_code"] == vpr.EXIT_INCOMPLETE


@pytest.mark.parametrize("state", ["ERROR", "LIMIT_REACHED", "INTERRUPTED"])
def test_successful_result_does_not_override_a_stopped_receipt(state):
    verdict = vpr.evaluate(
        answer("ok"), TEMPLATE, {"claims": [], "expectations": []}, {"status": state}
    )
    assert verdict["exit_code"] == vpr.EXIT_INCOMPLETE
    assert verdict["layers"]["run"]["verdict"] == state


@pytest.mark.parametrize("exit_code", [1, -9, "0", None, False, 0.0])
def test_completed_receipt_cannot_hide_nonzero_or_malformed_exit_code(exit_code):
    verdict = vpr.evaluate(
        answer("ok"),
        TEMPLATE,
        {"claims": [], "expectations": []},
        {"status": "COMPLETED", "exit_code": exit_code},
    )
    assert verdict["exit_code"] == vpr.EXIT_INCOMPLETE
    assert verdict["layers"]["run"]["verdict"] == "ERROR"


@pytest.mark.parametrize("receipt", [None, {"status": "COMPLETED"}])
def test_later_success_cannot_hide_an_earlier_terminal_error(receipt):
    events = answer("ok")
    events.insert(-1, result_event("", is_error=True, subtype="error_during_execution"))
    verdict = vpr.evaluate(events, TEMPLATE, {"claims": [], "expectations": []}, receipt)
    assert verdict["exit_code"] == vpr.EXIT_INCOMPLETE
    assert verdict["layers"]["run"]["verdict"] == "ERROR"


@pytest.mark.parametrize("receipt", [None, {"status": "COMPLETED"}])
def test_evaluate_command_reports_receipt_free_budget_failure(tmp_path, receipt):
    events = answer("ok")
    events[-1].update(is_error=True, subtype="error_max_budget_usd")
    source, output = tmp_path / "events.jsonl", tmp_path / "verdict.json"
    source.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    if receipt is not None:
        (tmp_path / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    assert vpr.main(["evaluate", "--events", str(source), "--out", str(output)]) == (
        vpr.EXIT_INCOMPLETE
    )
    assert json.loads(output.read_text())["layers"]["run"]["verdict"] == "LIMIT_REACHED"


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
import json, os, subprocess, sys, time
from pathlib import Path
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
if mode in ("tree", "orphan", "closed_pipes", "early_eof"):
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL if mode in ("closed_pipes", "early_eof") else None,
        stderr=subprocess.DEVNULL,
    )
    Path("tree-pids-" + mode + ".json").write_text(json.dumps([os.getpid(), child.pid]))
    if mode == "orphan":
        sys.exit(0)
    if mode == "tree":
        time.sleep(60)
    if mode == "early_eof":
        os.close(sys.stdout.fileno())
        time.sleep(60)
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


def _supervise(fake, tmp_path, mode, *, terminate=vpr.terminate_owned, **limits):
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
        terminate=terminate,
    )
    return receipt, run_dir


def _pid_running(pid):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258  # WAIT_TIMEOUT
        finally:
            kernel.CloseHandle(handle)
    # An orphaned zombie has stopped executing even if the host's init has not reaped it.
    state = subprocess.run(
        ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, timeout=5
    ).stdout.strip()
    return bool(state) and not state.startswith("Z")


def _wait_stopped(pid):
    deadline = time.monotonic() + 5
    while _pid_running(pid) and time.monotonic() < deadline:
        time.sleep(0.02)
    return not _pid_running(pid)


@pytest.fixture
def tree_cleanup(tmp_path):
    # Independent of the implementation under test, including failed assertions.
    yield
    for path in tmp_path.glob("tree-pids-*.json"):
        for pid in reversed(json.loads(path.read_text())):
            if _pid_running(pid):
                try:
                    os.kill(pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
                except ProcessLookupError:
                    pass
                assert _wait_stopped(pid), f"test descendant {pid} did not stop"


@pytest.mark.parametrize("mode", ["tree", "orphan", "closed_pipes", "early_eof"])
def test_cleanup_stops_descendants_even_after_leader_exit(fake, tmp_path, tree_cleanup, mode):
    receipt, _ = _supervise(fake, tmp_path, mode, wall_seconds=2)
    leader, descendant = json.loads((tmp_path / f"tree-pids-{mode}.json").read_text())
    assert not _pid_running(leader)
    assert _wait_stopped(descendant), f"descendant {descendant} survived {mode} cleanup"
    assert receipt["elapsed_seconds"] < 15
    if mode == "closed_pipes":
        assert receipt["status"] == "COMPLETED"
    elif mode == "orphan":
        # EOF may arrive with the leader's exit, or an inherited pipe can stay
        # open until the wall limit. Neither path has a successful result.
        assert receipt["status"] in ("ERROR", "LIMIT_REACHED")
    else:
        assert receipt["status"] == "LIMIT_REACHED"


def test_repeated_concurrent_cleanup_leaves_unrelated_process_alive(fake, tmp_path, tree_cleanup):
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])

    def repeated(process):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: vpr.terminate_owned(process), range(12)))
        vpr.terminate_owned(process)

    try:
        _supervise(fake, tmp_path, "tree", terminate=repeated, wall_seconds=2)
        _, descendant = json.loads((tmp_path / "tree-pids-tree.json").read_text())
        assert _wait_stopped(descendant)
        assert unrelated.poll() is None
    finally:
        unrelated.kill()
        unrelated.wait(timeout=5)


def test_cleanup_rejects_a_process_not_started_by_the_verifier():
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        with pytest.raises(ValueError, match="owned"):
            vpr.terminate_owned(unrelated)
        assert unrelated.poll() is None
    finally:
        unrelated.kill()
        unrelated.wait(timeout=5)


@pytest.mark.skipif(os.name == "nt", reason="POSIX session ownership")
def test_owned_process_has_its_own_posix_session():
    process = vpr._start_owned([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert os.getsid(process.pid) == process.pid
        assert os.getpgid(process.pid) == process.pid
        assert os.getpgid(process.pid) != os.getpgrp()
    finally:
        vpr.terminate_owned(process)
        process.wait(timeout=5)


def test_cleanup_racing_startup_or_fast_exit_is_bounded_and_repeatable():
    for _ in range(6):
        process = vpr._start_owned(
            [sys.executable, "-c", "pass"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(lambda _: vpr.terminate_owned(process), range(6)))
            process.wait(timeout=5)
            vpr.terminate_owned(process)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)


def test_unexpected_supervision_exception_also_cleans_the_tree(fake, tmp_path, tree_cleanup):
    def clock():
        if (tmp_path / "tree-pids-tree.json").is_file():
            raise RuntimeError("synthetic supervisor failure")
        return time.monotonic()

    run_dir = tmp_path / "exception"
    run_dir.mkdir()
    try:
        with pytest.raises(RuntimeError, match="synthetic supervisor failure"):
            vpr.supervise(
                fake("tree"),
                "input",
                run_dir,
                vpr.Limits(wall_seconds=10),
                cwd=tmp_path,
                clock=clock,
                poll_seconds=0.02,
            )
    finally:
        path = tmp_path / "tree-pids-tree.json"
        if path.is_file():
            assert all(_wait_stopped(pid) for pid in json.loads(path.read_text()))


def test_thread_start_failure_still_cleans_owned_process(fake, tmp_path, monkeypatch):
    started, cleaned = [], []
    original_start = vpr.threading.Thread.start

    def start(thread):
        if started:
            raise RuntimeError("synthetic thread startup failure")
        started.append(thread)
        original_start(thread)

    def terminate(process):
        cleaned.append(process)
        vpr.terminate_owned(process)

    monkeypatch.setattr(vpr.threading.Thread, "start", start)
    with pytest.raises(RuntimeError, match="synthetic thread startup failure"):
        _supervise(fake, tmp_path, "stall", terminate=terminate)
    assert cleaned and all(p.poll() is not None for p in cleaned)


@pytest.mark.skipif(os.name != "nt", reason="Windows job handles")
def test_failed_process_start_closes_its_windows_job(monkeypatch):
    job = vpr._WindowsJob()

    def fail(*args, **kwargs):
        raise OSError("synthetic process startup failure")

    try:
        monkeypatch.setattr(vpr, "_WindowsJob", lambda: job)
        monkeypatch.setattr(vpr.subprocess, "Popen", fail)
        with pytest.raises(OSError, match="synthetic process startup failure"):
            vpr._start_owned(["not-started"])
        assert job.handle is None
    finally:
        job.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows job admission")
def test_windows_launcher_does_not_execute_cli_when_ownership_is_unavailable(tmp_path):
    marker = tmp_path / "must-not-exist"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            vpr._WINDOWS_LAUNCHER,
            "missing-" + marker.name,
            sys.executable,
            "-c",
            "from pathlib import Path; Path('must-not-exist').touch()",
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert not marker.exists()


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
