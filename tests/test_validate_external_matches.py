"""validate_all() scans the user's other Espanso match/*.yml files (read-only)
and warns about triggers that collide with espansr templates or system triggers."""

from pathlib import Path
from unittest.mock import patch

from espansr.core.templates import Template
from espansr.integrations.validate import validate_all


def _espanso_dir(tmp_path: Path) -> Path:
    cfg = tmp_path / "espanso"
    (cfg / "match").mkdir(parents=True)
    return cfg


def _validate(templates, cfg):
    with patch("espansr.integrations.validate.get_template_manager") as mock_mgr:
        mock_mgr.return_value.iter_with_triggers.return_value = iter(templates)
        return validate_all(espanso_config_dir=cfg)


def test_warns_when_base_yml_defines_coms(tmp_path):
    cfg = _espanso_dir(tmp_path)
    (cfg / "match" / "base.yml").write_text(
        "matches:\n  - trigger: ':coms'\n    replace: 'mine'\n", encoding="utf-8"
    )
    result = _validate([Template(name="a", content="A", trigger=":ta")], cfg)

    assert all(w.severity == "warning" for w in result)
    assert len(result) == 1
    assert result[0].template_name == "system"
    assert "':coms'" in result[0].message
    assert "base.yml" in result[0].message
    assert "generated commands popup trigger" in result[0].message


def test_warns_when_external_file_defines_template_trigger(tmp_path):
    cfg = _espanso_dir(tmp_path)
    (cfg / "match" / "work.yml").write_text(
        "matches:\n  - triggers: [':sig', ':signature']\n    replace: 'x'\n", encoding="utf-8"
    )
    (cfg / "match" / "other.yaml").write_text(
        "matches:\n  - trigger: ':sig'\n    replace: 'y'\n", encoding="utf-8"
    )
    result = _validate([Template(name="Signature", content="A", trigger=":sig")], cfg)

    assert len(result) == 1
    assert result[0].severity == "warning"
    assert result[0].template_name == "Signature"
    assert "other.yaml, work.yml" in result[0].message


def test_skips_espansr_managed_files(tmp_path):
    cfg = _espanso_dir(tmp_path)
    for name in ("espansr.yml", "espansr-commands.yml", "espansr-launcher.yml", "espansr-sync.yml"):
        (cfg / "match" / name).write_text(
            "matches:\n  - trigger: ':coms'\n    replace: 'x'\n  - trigger: ':ta'\n"
            "    replace: 'y'\n",
            encoding="utf-8",
        )
    assert _validate([Template(name="a", content="A", trigger=":ta")], cfg) == []


def test_unreadable_or_odd_files_never_fail(tmp_path):
    cfg = _espanso_dir(tmp_path)
    (cfg / "match" / "broken.yml").write_text("matches: [\n  - trigger: ':ta'", encoding="utf-8")
    (cfg / "match" / "scalar.yml").write_text("just text\n", encoding="utf-8")
    (cfg / "match" / "list.yml").write_text("matches:\n  - 'not a mapping'\n", encoding="utf-8")
    (cfg / "match" / "binary.yml").write_bytes(b"\xff\xfe\x00bad")
    result = _validate([Template(name="a", content="A", trigger=":ta")], cfg)
    assert result == []


def test_missing_match_dir_is_fine(tmp_path):
    result = _validate([Template(name="a", content="A", trigger=":ta")], tmp_path / "nowhere")
    assert result == []


def test_no_espanso_config_dir_skips_scan():
    with (
        patch("espansr.integrations.validate.get_template_manager") as mock_mgr,
        patch("espansr.integrations.espanso.get_espanso_config_dir", return_value=None),
    ):
        mock_mgr.return_value.iter_with_triggers.return_value = iter(
            [Template(name="a", content="A", trigger=":ta")]
        )
        assert validate_all() == []


def test_detection_failure_never_breaks_validation():
    with (
        patch("espansr.integrations.validate.get_template_manager") as mock_mgr,
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            side_effect=RuntimeError("boom"),
        ),
    ):
        mock_mgr.return_value.iter_with_triggers.return_value = iter(
            [Template(name="a", content="A", trigger=":ta")]
        )
        assert validate_all() == []
