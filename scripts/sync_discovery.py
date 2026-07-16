#!/usr/bin/env python
"""Regenerate the static command-discovery surfaces from a single source.

Source of truth: :mod:`espansr.core.discovery`. This rewrites the ``:espansr``
quick-help content in ``templates/espansr_help.json`` and the generated
prompt-note list block in ``docs/TEMPLATES.md`` so they can never drift.

Usage::

    python scripts/sync_discovery.py            # rewrite the surfaces
    python scripts/sync_discovery.py --check     # exit 1 if they are stale
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from espansr.core.discovery import render_docs_note_list, render_quick_help

ROOT = Path(__file__).resolve().parents[1]
HELP_PATH = ROOT / "templates" / "espansr_help.json"
DOCS_PATH = ROOT / "docs" / "TEMPLATES.md"

BEGIN = (
    "<!-- BEGIN generated note list: run "
    "`python scripts/sync_discovery.py --apply` after changing templates -->"
)
END = "<!-- END generated note list -->"


def _expected_help_text() -> str:
    data = json.loads(HELP_PATH.read_text(encoding="utf-8"))
    data["content"] = render_quick_help()
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _expected_docs_text() -> str:
    text = DOCS_PATH.read_text(encoding="utf-8")
    block = f"{BEGIN}\n{render_docs_note_list()}\n{END}"
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(f"Missing generated-note-list markers in {DOCS_PATH.relative_to(ROOT)}")
    return pattern.sub(lambda _match: block, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift and exit non-zero instead of rewriting files.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite the discovery surfaces (default when --check is absent).",
    )
    args = parser.parse_args()

    help_expected = _expected_help_text()
    docs_expected = _expected_docs_text()

    drift = []
    if HELP_PATH.read_text(encoding="utf-8") != help_expected:
        drift.append("templates/espansr_help.json")
    if DOCS_PATH.read_text(encoding="utf-8") != docs_expected:
        drift.append("docs/TEMPLATES.md")

    if args.check:
        if drift:
            print("Discovery surfaces are out of sync:", ", ".join(drift))
            print("Run: python scripts/sync_discovery.py")
            return 1
        print("Discovery surfaces are in sync.")
        return 0

    HELP_PATH.write_text(help_expected, encoding="utf-8")
    DOCS_PATH.write_text(docs_expected, encoding="utf-8")
    print("Regenerated:", ", ".join(drift) if drift else "no changes needed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
