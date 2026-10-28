#!/usr/bin/env python
"""Run one isolated receiving-model sample of a bundled prompt and judge its evidence.

Maintainer verification only: this is not product behavior, CI never runs the
``run`` command, and ``run`` spends real model budget. ``run`` sends a
template's exact content, one fixed isolation preface and one example to the
installed Claude Code CLI with every tool disabled, then supervises wall time,
public assistant text and CLI-reported cost. ``evaluate`` judges saved events
in separate layers:

- run: COMPLETED, LIMIT_REACHED, INTERRUPTED or ERROR, never a quality verdict.
- execution: actual tool calls come only from structured protocol events. Text
  that merely looks like a tool call, a tool result or an approval is flagged
  for review and is never execution evidence.
- structural: the template's output contract; N/A when none is declared.
- semantic: reviewer-recorded claims and expectations, with side-effect claims
  checked against the execution evidence. Keyword-found candidate claims are a
  review aid only; they never decide a verdict.

Usage::

    python scripts/verify_prompt_receiver.py run --template :sample \\
        --example-file example.txt --model MODEL --effort LEVEL --out RUN_DIR
    python scripts/verify_prompt_receiver.py evaluate --events RUN_DIR/events.jsonl \\
        --template :sample [--review review.json] --out verdict.json

``run`` refuses an existing ``--out`` directory and ``evaluate`` refuses an
existing ``--out`` file, so a recorded result is never overwritten.

Exit codes: 0 every judged layer passed (N/A allowed); 1 a layer failed;
2 review still needed; 3 the run did not complete, or a usage error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from espansr.core.output_contract import check_output, normalize_contract  # noqa: E402

ISOLATION_PREFACE = (
    "Isolated plain-chat example. No tools or external actions are available. "
    "Deliver in chat; claim no execution, writes, approvals or delivery without "
    "observed evidence."
)
SIDE_EFFECT_KINDS = ("execution", "test", "write", "approval", "delivery")
# ``--permission-mode manual`` is reported as "default" in the init event (CLI 2.1.287).
MANUAL_MODES = ("manual", "default")
EXIT_PASS, EXIT_FAIL, EXIT_REVIEW, EXIT_INCOMPLETE = 0, 1, 2, 3

# Markup that imitates a tool protocol inside ordinary assistant text.
PSEUDO_MARKUP = re.compile(r"<\s*/?\s*(?:invoke|function_calls|function_results|parameter)\b", re.I)
# Review aid only: sentences that may describe a completed action.
CLAIM_VERBS = re.compile(
    r"\b(?:ran|run|executed|saved|wrote|written|created|committed|pushed|merged|installed|"
    r"deployed|approved|listed|tested|sent|published|deleted)\b",
    re.I,
)
FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Limits:
    """Declared per-sample limits; the CLI enforces only the budget itself."""

    wall_seconds: float = 300.0
    max_public_text_bytes: int = 64 * 1024
    max_budget_usd: float = 1.0


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ── Input and command ────────────────────────────────────────────────────────


def load_template(trigger: str, templates_dir: Path = ROOT / "templates") -> dict:
    """Return the bundled template JSON whose trigger, name or file stem matches."""
    wanted = {trigger, ":" + trigger.lstrip(":")}
    for path in sorted(templates_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("trigger") in wanted or data.get("name") == trigger or path.stem == trigger:
            return {**data, "_path": path.relative_to(templates_dir.parent).as_posix()}
    raise LookupError(f"no bundled template matches {trigger!r}")


def build_input(content: str, example: str, preface: str = ISOLATION_PREFACE) -> tuple[str, dict]:
    """Exact content, then the preface, then the example; each part hashed separately."""
    text = content + preface + "\n\n" + example.rstrip("\n") + "\n"
    identities = {
        "content_sha256": _sha256(content),
        "preface_sha256": _sha256(preface),
        "example_sha256": _sha256(example),
        "input_sha256": _sha256(text),
    }
    return text, identities


def build_argv(cli: str, *, model: str, effort: str, budget_usd: float, session_id: str) -> list:
    """Claude Code print mode with no tools, no plan mode, no fallback model."""
    return [
        cli,
        "--print",
        "--model",
        model,
        "--effort",
        effort,
        "--session-id",
        session_id,
        "--no-session-persistence",
        "--tools",
        "",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--disable-slash-commands",
        "--no-chrome",
        "--permission-mode",
        "manual",
        "--permission-prompts",
        "none",
        "--max-budget-usd",
        f"{budget_usd:g}",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
    ]


# ── Supervision ──────────────────────────────────────────────────────────────


def public_event(event: dict) -> dict | None:
    """The event without hidden reasoning; partial stream chunks are not kept."""
    if event.get("type") == "stream_event":
        return None
    message = event.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), list):
        message["content"] = [
            block
            for block in message["content"]
            if not (
                isinstance(block, dict) and block.get("type") in ("thinking", "redacted_thinking")
            )
        ]
    return event


def text_delta_bytes(event: dict) -> int:
    """UTF-8 bytes of public text in one partial chunk (reasoning deltas count 0)."""
    if event.get("type") != "stream_event":
        return 0
    delta = (event.get("event") or {}).get("delta") or {}
    if delta.get("type") == "text_delta":
        return len(str(delta.get("text", "")).encode("utf-8"))
    return 0


def _assistant_text_bytes(event: dict) -> int:
    if event.get("type") != "assistant":
        return 0
    content = (event.get("message") or {}).get("content") or []
    return sum(
        len(str(b.get("text", "")).encode("utf-8"))
        for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    )


def terminate_owned(process: subprocess.Popen) -> None:
    """Stop only the process this supervisor started, with its own children."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        process.kill()


def _init_problem(init: dict, model: str | None, modes: tuple | None) -> str | None:
    if init.get("tools"):
        return f"tools were available: {init.get('tools')}"
    if model and init.get("model") != model:
        return f"init model {init.get('model')!r} differs from requested {model!r}"
    if modes and init.get("permissionMode") not in modes:
        return f"permission mode {init.get('permissionMode')!r}, expected one of {modes}"
    return None


def supervise(
    argv: list,
    input_text: str,
    run_dir: Path,
    limits: Limits,
    *,
    cwd: Path,
    model: str | None = None,
    permission_modes: tuple | None = None,
    terminate: Callable[[subprocess.Popen], None] = terminate_owned,
    clock: Callable[[], float] = time.monotonic,
    poll_seconds: float = 0.2,
) -> dict:
    """Run argv once, keep public events, and stop the owned process at any limit.

    Wall time is checked while waiting on a queue, so a silent child cannot
    stall enforcement. Nothing is retried and no other model is tried.
    """
    events_path = run_dir / "events.jsonl"
    stderr_path = run_dir / "stderr.log"
    started, started_at = clock(), _now()
    status, reason = "COMPLETED", ""
    partial_bytes = final_bytes = 0
    init: dict = {}
    result: dict | None = None
    lines: queue.Queue = queue.Queue()

    with (
        events_path.open("x", encoding="utf-8") as out,
        stderr_path.open("x", encoding="utf-8") as err,
    ):
        process = subprocess.Popen(
            argv,
            cwd=str(cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=err,
            encoding="utf-8",
            errors="replace",
        )

        def feed() -> None:
            try:
                process.stdin.write(input_text)
                process.stdin.close()
            except OSError:
                pass

        def read() -> None:
            for raw in process.stdout:
                lines.put(raw)
            lines.put(None)

        threading.Thread(target=feed, daemon=True).start()
        reader = threading.Thread(target=read, daemon=True)
        reader.start()

        def handle(raw: str, counting: bool) -> None:
            nonlocal partial_bytes, final_bytes, init, result
            try:
                event = json.loads(raw)
            except ValueError:
                out.write(json.dumps({"type": "unparsed_line", "text": raw.rstrip("\n")}) + "\n")
                return
            if counting:
                partial_bytes += text_delta_bytes(event)
                final_bytes += _assistant_text_bytes(event)
            kept = public_event(event)
            if kept is None:
                return
            out.write(json.dumps(kept, ensure_ascii=False) + "\n")
            out.flush()
            if kept.get("type") == "system" and kept.get("subtype") == "init":
                init = kept
            elif kept.get("type") == "result":
                result = kept

        try:
            while True:
                remaining = started + limits.wall_seconds - clock()
                if remaining <= 0:
                    status, reason = "LIMIT_REACHED", "wall_time"
                    break
                try:
                    raw = lines.get(timeout=min(poll_seconds, remaining))
                except queue.Empty:
                    continue
                if raw is None:
                    break
                handle(raw, counting=True)
                if init and not reason:
                    problem = _init_problem(init, model, permission_modes)
                    if problem:
                        status, reason = "ERROR", problem
                        break
                if max(partial_bytes, final_bytes) > limits.max_public_text_bytes:
                    status, reason = "LIMIT_REACHED", "public_text"
                    break
        except KeyboardInterrupt:
            status, reason = "INTERRUPTED", "keyboard_interrupt"
        if status != "COMPLETED":
            terminate(process)
        try:
            exit_code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            terminate(process)
            exit_code = process.wait(timeout=30)
        reader.join(timeout=10)
        while True:  # keep evidence that arrived before the stop, without counting it
            try:
                raw = lines.get_nowait()
            except queue.Empty:
                break
            if raw is not None:
                handle(raw, counting=False)

    cost = (result or {}).get("total_cost_usd")
    subtype = str((result or {}).get("subtype", ""))
    if status == "COMPLETED":
        if "budget" in subtype:
            status, reason = "LIMIT_REACHED", "budget"
        elif result is None:
            status, reason = "ERROR", "no result event"
        elif exit_code != 0 or result.get("is_error"):
            status, reason = "ERROR", f"exit {exit_code}; result subtype {subtype!r}"
        else:
            used = sorted((result.get("modelUsage") or {}).keys())
            if model and used and used != [model]:
                status, reason = "ERROR", f"model usage {used} differs from requested {model!r}"

    receipt = {
        "status": status,
        "reason": reason,
        "started_at": started_at,
        "completed_at": _now(),
        "elapsed_seconds": round(clock() - started, 3),
        "exit_code": exit_code,
        "limits": asdict(limits),
        "public_text_bytes": {"partial_deltas": partial_bytes, "assistant_blocks": final_bytes},
        "cost_usd": cost,
        "budget_overshoot_usd": (
            round(cost - limits.max_budget_usd, 6)
            if isinstance(cost, (int, float)) and cost > limits.max_budget_usd
            else 0.0
        ),
        "result": {
            "subtype": subtype or None,
            "is_error": (result or {}).get("is_error"),
            "num_turns": (result or {}).get("num_turns"),
            "permission_denials": len((result or {}).get("permission_denials") or []),
            "model_usage": {
                name: {"canonical_model": usage.get("canonicalModel")}
                for name, usage in ((result or {}).get("modelUsage") or {}).items()
            },
        },
        "init": {
            key: init.get(key)
            for key in (
                "model",
                "tools",
                "permissionMode",
                "claude_code_version",
                "per_turn_effort_active",
                "memory_paths",
            )
        },
    }
    if result is not None:
        (run_dir / "output.md").write_text(str(result.get("result", "")), encoding="utf-8")
    return receipt


# ── Evaluation ───────────────────────────────────────────────────────────────


def load_events(path: Path) -> list:
    """Parsed events from a JSON Lines file (blank lines skipped)."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _blocks(event: dict) -> Iterable[dict]:
    content = (event.get("message") or {}).get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def protocol(events: list) -> dict:
    """Structured protocol facts: init, real calls with correlated results, text."""
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    calls, outcomes, texts = {}, {}, []
    for event in events:
        for block in _blocks(event):
            if event.get("type") == "assistant" and block.get("type") == "tool_use":
                calls[block.get("id")] = block.get("name")
            elif event.get("type") == "assistant" and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
            elif event.get("type") == "user" and block.get("type") == "tool_result":
                outcomes[block.get("tool_use_id")] = "failed" if block.get("is_error") else "ok"
    denied = {
        d.get("tool_use_id"): d.get("tool_name") for d in (result.get("permission_denials") or [])
    }
    actions = []
    for call_id, name in calls.items():
        outcome = "denied" if call_id in denied else outcomes.get(call_id, "unanswered")
        actions.append({"id": call_id, "tool": name, "outcome": outcome})
    return {
        "init": {k: init.get(k) for k in ("model", "tools", "permissionMode")},
        "tools_available": init.get("tools"),
        "actions": actions,
        "orphan_results": sorted(str(i) for i in outcomes if i not in calls),
        "denials": [{"id": i, "tool": n} for i, n in denied.items()],
        "public_text": "\n\n".join(texts),
        "final_text": str(result.get("result", "")) if result else "",
        "has_result": bool(result),
    }


def _outside_fences(text: str) -> list:
    """(line number, line) pairs that are not inside a fenced code block."""
    kept, fenced = [], False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            kept.append((number, line))
    return kept


def pseudo_markup(text: str) -> dict:
    """Tool-protocol imitation in prose (flagged) versus inside code fences (quoted)."""
    total = len(PSEUDO_MARKUP.findall(text))
    flagged = [
        {"line": n, "snippet": line.strip()[:120]}
        for n, line in _outside_fences(text)
        if PSEUDO_MARKUP.search(line)
    ]
    outside = sum(len(PSEUDO_MARKUP.findall(line)) for _, line in _outside_fences(text))
    return {"outside_fences": outside, "inside_fences": total - outside, "first": flagged[:5]}


def claim_candidates(text: str) -> list:
    """Sentences outside code fences that may describe completed actions (review aid)."""
    prose = " ".join(line for _, line in _outside_fences(text))
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    return [s.strip() for s in sentences if CLAIM_VERBS.search(s) and len(s.strip()) > 3]


def execution_verdict(facts: dict) -> dict:
    """Isolation holds only when the run had no tools and no actual tool activity."""
    tools = facts["tools_available"]
    activity = facts["actions"] or facts["denials"] or facts["orphan_results"]
    if tools is None:
        verdict, note = "UNKNOWN", "no init event, so tool availability is unattested"
    elif tools == [] and activity:
        verdict, note = "FAIL", "actual tool activity in a tools-disabled run"
    elif tools == []:
        verdict, note = "PASS", "tools disabled and no actual tool activity"
    else:
        verdict, note = "N/A", "tools were enabled; judge actions against readback"
    return {"verdict": verdict, "note": note, "actions": facts["actions"]}


def structural_verdict(template: dict | None, final_text: str) -> dict:
    """The template's output contract; N/A when the template declares none."""
    if template is None:
        return {"verdict": "NOT_CHECKED", "failures": []}
    if normalize_contract(template.get("output_contract")) is None:
        return {"verdict": "N/A", "failures": []}
    report = check_output(template["output_contract"], final_text)
    return {
        "verdict": "PASS" if report.passed else "FAIL",
        "failures": [f.message for f in report.failures],
    }


def judge_claim(claim: dict, public_text: str, facts: dict) -> str:
    """Check one reviewer-recorded claim against the text and execution evidence."""
    quote = str(claim.get("quote", ""))
    if not quote or quote not in public_text:
        return "UNANCHORED"
    if claim.get("kind") not in SIDE_EFFECT_KINDS:
        return "INVALID_KIND"
    if not claim.get("asserted", True):
        return "CONSISTENT"
    succeeded = [a for a in facts["actions"] if a["outcome"] == "ok"]
    if facts["tools_available"] == [] and not succeeded:
        return "CONTRADICTED"
    if claim.get("evidence"):
        return "SUPPORTED"
    return "UNVERIFIED"


def semantic_verdict(facts: dict, review: dict | None) -> dict:
    """Reviewer findings checked against execution; keyword hits only request review."""
    text = facts["public_text"] or facts["final_text"]
    markup = pseudo_markup(text)
    candidates = claim_candidates(text)
    if review is None:
        return {
            "verdict": "NEEDS_REVIEW",
            "reasons": ["no review recorded"],
            "claims": [],
            "expectations": [],
            "pseudo_markup": markup,
            "unreviewed_candidates": candidates,
        }
    claims = [{**c, "status": judge_claim(c, text, facts)} for c in review.get("claims", [])]
    covered = [c["quote"] for c in claims] + [str(d) for d in review.get("dismissed", [])]
    unreviewed = [s for s in candidates if not any(q and q in s for q in covered)]
    expectations = review.get("expectations", [])
    reasons = []
    if any(c["status"] == "CONTRADICTED" for c in claims):
        reasons.append("a claimed side effect contradicts the execution evidence")
    if any(e.get("verdict") == "FAIL" for e in expectations):
        reasons.append("a reviewed expectation failed")
    if reasons:
        verdict = "FAIL"
    else:
        if any(c["status"] in ("UNANCHORED", "INVALID_KIND", "UNVERIFIED") for c in claims):
            reasons.append("a claim is unanchored, has an unknown kind, or is unverified")
        if any(e.get("verdict") != "PASS" for e in expectations):
            reasons.append("an expectation is not PASS")
        if unreviewed:
            reasons.append("candidate claim sentences are unreviewed")
        if markup["outside_fences"] and not review.get("pseudo_markup_reviewed"):
            reasons.append("tool-protocol imitation in prose is unreviewed")
        verdict = "NEEDS_REVIEW" if reasons else "PASS"
    return {
        "verdict": verdict,
        "reasons": reasons,
        "claims": claims,
        "expectations": expectations,
        "pseudo_markup": markup,
        "unreviewed_candidates": unreviewed,
    }


def evaluate(
    events: list, template: dict | None, review: dict | None, receipt: dict | None = None
) -> dict:
    """All verdict layers, kept separate, plus the overall exit code."""
    facts = protocol(events)
    layers = {
        "run": {"verdict": (receipt or {}).get("status", "NOT_RECORDED")},
        "execution": execution_verdict(facts),
        "structural": structural_verdict(template, facts["final_text"]),
        "semantic": semantic_verdict(facts, review),
    }
    run_state = layers["run"]["verdict"]
    verdicts = [layers[k]["verdict"] for k in ("execution", "structural", "semantic")]
    if run_state not in ("COMPLETED", "NOT_RECORDED") or not facts["has_result"]:
        code = EXIT_INCOMPLETE
    elif "FAIL" in verdicts:
        code = EXIT_FAIL
    elif any(v in ("NEEDS_REVIEW", "UNKNOWN", "NOT_CHECKED") for v in verdicts):
        code = EXIT_REVIEW
    else:
        code = EXIT_PASS
    return {"layers": layers, "exit_code": code}


# ── Command line ─────────────────────────────────────────────────────────────


def _write_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def cmd_run(args) -> int:
    """Run one sample into a new directory and print its receipt."""
    cli = args.cli or shutil.which("claude")
    if not cli:
        print("claude CLI not found; pass --cli", file=sys.stderr)
        return EXIT_INCOMPLETE
    template = load_template(args.template)
    example = Path(args.example_file).read_text(encoding="utf-8")
    text, identities = build_input(template["content"], example)
    limits = Limits(args.wall_seconds, args.max_text_bytes, args.max_budget_usd)
    session_id = str(uuid.uuid4())
    argv = build_argv(
        cli,
        model=args.model,
        effort=args.effort,
        budget_usd=limits.max_budget_usd,
        session_id=session_id,
    )
    run_dir = Path(args.out)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "input.txt").write_text(text, encoding="utf-8", newline="")
    intent = {
        "created_at": _now(),
        "template": template["_path"],
        "trigger": template.get("trigger"),
        "identities": identities,
        "requested_model": args.model,
        "requested_effort": args.effort,
        "effort_attestation": "requested only; the stream does not report the effort level",
        "session_id": session_id,
        "argv": argv,
        "limits": asdict(limits),
    }
    _write_new(run_dir / "intent.json", intent)
    workdir = Path(tempfile.mkdtemp(prefix="espansr-receiver-"))
    try:
        receipt = supervise(
            argv,
            text,
            run_dir,
            limits,
            cwd=workdir,
            model=args.model,
            permission_modes=MANUAL_MODES,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    receipt = {**receipt, "session_id": session_id, "cwd": "temporary empty directory"}
    _write_new(run_dir / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return EXIT_PASS if receipt["status"] == "COMPLETED" else EXIT_INCOMPLETE


def cmd_evaluate(args) -> int:
    """Judge saved events and write the verdict to a new file."""
    events_path = Path(args.events)
    receipt_path = events_path.parent / "receipt.json"
    receipt = (
        json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
    )
    review = json.loads(Path(args.review).read_text(encoding="utf-8")) if args.review else None
    template = load_template(args.template) if args.template else None
    verdict = evaluate(load_events(events_path), template, review, receipt)
    _write_new(Path(args.out), verdict)
    print(json.dumps({k: v["verdict"] for k, v in verdict["layers"].items()}, indent=2))
    return verdict["exit_code"]


def main(argv: list | None = None) -> int:
    """Parse arguments and dispatch to ``run`` or ``evaluate``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run one isolated receiving-model sample")
    run.add_argument("--template", required=True, help="bundled template trigger")
    run.add_argument("--example-file", required=True, help="example text placed after the preface")
    run.add_argument("--model", required=True, help="exact model; no fallback is configured")
    run.add_argument("--effort", required=True, help="requested effort level")
    run.add_argument("--out", required=True, help="new directory for this run's receipts")
    run.add_argument("--cli", help="path to the claude executable (default: on PATH)")
    run.add_argument("--wall-seconds", type=float, default=Limits.wall_seconds)
    run.add_argument("--max-text-bytes", type=int, default=Limits.max_public_text_bytes)
    run.add_argument("--max-budget-usd", type=float, default=Limits.max_budget_usd)
    run.set_defaults(handler=cmd_run)
    ev = sub.add_parser("evaluate", help="judge saved events in separate layers")
    ev.add_argument("--events", required=True, help="events.jsonl written by run")
    ev.add_argument("--template", help="bundled template trigger owning the output contract")
    ev.add_argument("--review", help="reviewer claims and expectations (JSON)")
    ev.add_argument("--out", required=True, help="new file for the verdict JSON")
    ev.set_defaults(handler=cmd_evaluate)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (FileExistsError, LookupError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
