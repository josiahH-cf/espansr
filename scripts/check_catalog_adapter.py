"""Check one exact OA adapter source without importing/changing an OA install.

The owner supplies the pinned catalog.py from its qualified candidate. This
checks the existing adapter-v1 read/prepare contract and frozen JSON replay;
it does not claim the OA service already consumes the additive descriptor.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

from espansr.core.capability_catalog import (
    build_catalog,
    freeze_definition,
    publish_catalog,
    render_frozen,
)

ROOT = Path(__file__).resolve().parents[1]


def check(adapter_file: Path, expected_sha256: str) -> dict:
    raw = adapter_file.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise ValueError("OA adapter source version changed")
    spec = importlib.util.spec_from_file_location("_qualified_oa_adapter", adapter_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.INTERFACE == "espansr-adapter-v1"
    catalog = build_catalog(ROOT / "templates")
    legacy = module.EspansrCatalog(ROOT / "templates").load()
    templates, workflows = 0, 0
    for entry in catalog["entries"]:
        assert entry["usable"]
        if entry["kind"] == "template":
            record = legacy.template(entry["template_id"])
            assert record and record.error is None
            assert record.digest == entry["source_byte_sha256"]
            assert record.capability_id == entry["capability_id"]
            assert record.description == entry["description"]
            assert list(record.accepts) == entry["accepts"]
            assert list(record.produces) == entry["produces"]
            assert list(record.variables) == entry["variables"]
            assert record.output_contract == entry["output_contract"]
            values = {v: f"[{v}]" for v in entry["variables"]}
            frozen = freeze_definition(
                catalog,
                entry["id"],
                ROOT / "templates",
                values=values,
                context_binding={"request_id": "fixture:1"},
            )
            rendered = render_frozen(json.loads(json.dumps(frozen)))
            # adapter-v1 trims trailing newlines for prompts without its user
            # marker; publication/freezing retains the original exact bytes.
            expected = rendered if module.USER_MARKER in rendered else rendered.rstrip("\n")
            assert expected == legacy.prepare(entry["template_id"], "", values=values).prepared
            templates += 1
        else:
            record = legacy.workflows[entry["workflow_id"]]
            assert not record.errors and record.digest == entry["source_byte_sha256"]
            workflows += 1
    scratch_parent = ROOT / ".tmp_pytest"
    scratch_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="adapter-", dir=scratch_parent) as scratch:
        source, installed = Path(scratch) / "source", Path(scratch) / "installed"
        source.mkdir()
        data = {
            "name": "Sample",
            "trigger": ":sample",
            "content": "Plan {{goal}}",
            "variables": [{"name": "goal"}],
        }
        (source / "sample.json").write_text(json.dumps(data), encoding="utf-8")
        shutil.copytree(source, installed)
        published = publish_catalog(source, installed)
        old = module.EspansrCatalog(installed).load().prepare("sample", "", values={"goal": "A"})
        frozen = freeze_definition(
            published,
            "template:sample",
            installed,
            values={"goal": "A"},
            context_binding={"request_id": "same:1"},
        )
        data["content"] = "New {{goal}}"
        (source / "sample.json").write_text(json.dumps(data), encoding="utf-8")
        shutil.copy2(source / "sample.json", installed / "sample.json")
        publish_catalog(source, installed)
        assert render_frozen(json.loads(json.dumps(frozen))) == old.prepared == "Plan A"
        assert (
            module.EspansrCatalog(installed)
            .load()
            .prepare("sample", "", values={"goal": "A"})
            .prepared
            == "New A"
        )
    return {
        "interface": "espansr-oa-adapter-qualification-v1",
        "adapter_sha256": actual,
        "templates_compared": templates,
        "workflows_compared": workflows,
        "prepare_and_frozen_replay": "passed",
        "boundary": "private-source-fixtures",
        "live_oa_consumer": "unobserved",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-file", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.adapter_file, args.expected_sha256), indent=2))
