"""Publish every bundled note through the real sync path and read it back.

Copies ``templates/*.json`` into the isolated live store, runs
``sync_to_espanso()`` into a tmp Espanso config (the conftest fixtures stub
the daemon restart), and checks the generated ``espansr.yml`` carries every
trigger exactly once with the prompt text unchanged for variable-free notes.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import yaml

from espansr.core.config import get_templates_dir

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"


def test_bundled_notes_roundtrip_through_espanso_yaml(tmp_path):
    from espansr.integrations.espanso import sync_to_espanso

    bundled = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in TEMPLATES_DIR.glob("*.json")
    }
    assert bundled
    live = get_templates_dir()
    for path in TEMPLATES_DIR.glob("*.json"):
        shutil.copy(path, live / path.name)

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)
    with patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir):
        assert sync_to_espanso() is True

    generated = yaml.safe_load((match_dir / "espansr.yml").read_text(encoding="utf-8"))
    matches = generated["matches"]

    # Every trigger appears exactly once, and nothing else was published.
    triggers = [match["trigger"] for match in matches]
    assert len(triggers) == len(set(triggers))
    assert sorted(triggers) == sorted(data["trigger"] for data in bundled.values())

    by_trigger = {match["trigger"]: match for match in matches}
    variable_free = 0
    for filename, data in bundled.items():
        match = by_trigger[data["trigger"]]
        if data.get("variables"):
            assert match["vars"], f"{filename}: variables were not published"
            continue
        assert match["replace"] == data["content"], f"{filename}: content changed in transit"
        assert "vars" not in match, f"{filename}: unexpected vars entry"
        variable_free += 1
    assert variable_free > 0
