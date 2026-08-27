import json
from pathlib import Path

import pytest

from espansr.core.atomic import atomic_copy, atomic_write_bytes
from espansr.core.templates import Template, TemplateManager


def test_atomic_write_replaces_complete_file_and_leaves_no_temporary_file(tmp_path):
    target = tmp_path / "research_report.json"
    target.write_bytes(b"old")

    atomic_write_bytes(target, b"complete replacement")

    assert target.read_bytes() == b"complete replacement"
    assert list(tmp_path.glob(".research_report.json.*.tmp")) == []


def test_atomic_write_preserves_previous_file_when_replace_fails(tmp_path, monkeypatch):
    target = tmp_path / "meta.json"
    target.write_bytes(b"previous")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("espansr.core.atomic.os.replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        atomic_write_bytes(target, b"new")

    assert target.read_bytes() == b"previous"
    assert list(tmp_path.glob(".meta.json.*.tmp")) == []


def test_atomic_copy_uses_one_complete_source_snapshot(tmp_path):
    source = tmp_path / "bundled.json"
    destination = tmp_path / "live.json"
    source.write_bytes(b'{"name":"Research","content":"trusted"}')

    atomic_copy(source, destination)

    assert destination.read_bytes() == source.read_bytes()
    assert list(tmp_path.glob(".live.json.*.tmp")) == []


def test_template_manager_save_and_version_remain_valid_json(tmp_path):
    manager = TemplateManager(tmp_path)
    template = Template(name="Research Report", content="trusted policy")

    assert manager.save(template)
    assert manager.create_version(template) is not None

    assert (
        json.loads((tmp_path / "research_report.json").read_text(encoding="utf-8"))["content"]
        == "trusted policy"
    )
    version = tmp_path / "_versions" / "research_report" / "v1.json"
    assert json.loads(version.read_text(encoding="utf-8"))["template_data"]["content"] == (
        "trusted policy"
    )


def test_move_writes_destination_before_removing_source(tmp_path, monkeypatch):
    manager = TemplateManager(tmp_path)
    template = Template(name="Context", content="v1")
    assert manager.save(template)
    old_path = template._path
    assert old_path is not None

    observed = {}
    real_unlink = Path.unlink

    def observing_unlink(path: Path, *args, **kwargs):
        observed["destination_exists"] = (tmp_path / "flows" / "context.json").exists()
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", observing_unlink)

    assert manager.save_to_folder(template, "flows")
    assert observed["destination_exists"] is True
    assert not old_path.exists()
