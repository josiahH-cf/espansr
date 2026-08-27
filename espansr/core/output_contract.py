"""Structural output contracts for model-generated responses.

An output contract is optional machine-readable metadata on a capability
describing structural obligations its generated output must contain: required
sections, required literal or regular-expression markers with occurrence
bounds, and forbidden markers. Checking is read-only, reports every unmet
obligation (never just the first), and proves structural conformance only —
it never claims semantic quality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

OUTPUT_CONTRACT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ContractFailure:
    """One unmet structural obligation."""

    kind: str  # "section" | "marker" | "forbidden" | "contract"
    message: str


@dataclass
class ContractReport:
    """Every failure found while checking one output against one contract."""

    failures: List[ContractFailure] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def summary(self) -> str:
        if self.passed:
            return (
                "OUTPUT CONTRACT: PASS (structural conformance only — this does "
                "not prove semantic correctness)"
            )
        return (
            f"OUTPUT CONTRACT: FAIL ({len(self.failures)} unmet structural "
            "obligation(s); structural checks do not judge semantic quality)"
        )


def _normalize_markers(raw: Any) -> List[Dict[str, Any]]:
    markers: List[Dict[str, Any]] = []
    if not isinstance(raw, list):
        return markers
    for item in raw:
        if not isinstance(item, dict):
            continue
        pattern = item.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            continue
        marker: Dict[str, Any] = {
            "pattern": pattern,
            "regex": bool(item.get("regex", False)),
            "min_count": item.get("min_count", 1),
            "message": str(item.get("message", "") or ""),
        }
        if isinstance(item.get("max_count"), int):
            marker["max_count"] = item["max_count"]
        if not isinstance(marker["min_count"], int) or marker["min_count"] < 0:
            marker["min_count"] = 1
        markers.append(marker)
    return markers


def normalize_contract(data: Any) -> Optional[Dict[str, Any]]:
    """Return a normalized contract dict, or None when *data* is not a contract.

    A usable contract is a dict declaring at least one obligation. Malformed
    entries inside it are skipped conservatively; unknown keys are ignored and
    never become executable behavior.
    """
    if not isinstance(data, dict) or not data:
        return None
    contract = {
        "schema": data.get("schema", OUTPUT_CONTRACT_SCHEMA_VERSION),
        "artifact_type": str(data.get("artifact_type", "") or ""),
        "required_sections": [
            str(s) for s in data.get("required_sections", []) if isinstance(s, str) and s
        ],
        "required_markers": _normalize_markers(data.get("required_markers")),
        "forbidden_markers": _normalize_markers(data.get("forbidden_markers")),
    }
    if (
        not contract["required_sections"]
        and not contract["required_markers"]
        and not contract["forbidden_markers"]
    ):
        return None
    return contract


def _count_marker(marker: Dict[str, Any], text: str) -> Optional[int]:
    """Count occurrences of *marker* in *text*; None when the regex is invalid."""
    pattern = marker["pattern"]
    if marker["regex"]:
        try:
            return len(re.findall(pattern, text))
        except re.error:
            return None
    return text.count(pattern)


def _section_present(name: str, text: str) -> bool:
    pattern = r"^[ \t]*#{0,6}[ \t]*" + re.escape(name)
    return re.search(pattern, text, re.MULTILINE) is not None


def check_output(contract: Any, text: str) -> ContractReport:
    """Check *text* against *contract*, reporting every unmet obligation."""
    report = ContractReport()
    normalized = normalize_contract(contract)
    if normalized is None:
        report.failures.append(
            ContractFailure(
                kind="contract",
                message="no usable output contract was supplied",
            )
        )
        return report

    for section in normalized["required_sections"]:
        if not _section_present(section, text):
            report.failures.append(
                ContractFailure(kind="section", message=f"missing required section: {section}")
            )

    for marker in normalized["required_markers"]:
        count = _count_marker(marker, text)
        if count is None:
            report.failures.append(
                ContractFailure(
                    kind="contract",
                    message=f"invalid marker pattern in contract: {marker['pattern']}",
                )
            )
            continue
        label = marker["message"] or f"required marker: {marker['pattern']}"
        if count < marker["min_count"]:
            report.failures.append(
                ContractFailure(
                    kind="marker",
                    message=(f"{label} (found {count}, need at least {marker['min_count']})"),
                )
            )
        elif "max_count" in marker and count > marker["max_count"]:
            report.failures.append(
                ContractFailure(
                    kind="marker",
                    message=(f"{label} (found {count}, allowed at most {marker['max_count']})"),
                )
            )

    for marker in normalized["forbidden_markers"]:
        count = _count_marker(marker, text)
        if count is None:
            report.failures.append(
                ContractFailure(
                    kind="contract",
                    message=f"invalid marker pattern in contract: {marker['pattern']}",
                )
            )
            continue
        if count > 0:
            label = marker["message"] or f"forbidden marker present: {marker['pattern']}"
            report.failures.append(ContractFailure(kind="forbidden", message=label))

    return report
