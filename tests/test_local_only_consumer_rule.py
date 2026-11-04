"""The flag and the rule a program reading the template folder itself relies on.

espansr cannot stop another program from reading its live template files. What
it owes such a consumer is a flag it can read in every private file and one
exact rule, documented in docs/CAPABILITY_CATALOG.md ("Local-only templates
for consumers") and mirrored without imports in scripts/deliver.py.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from espansr.core import capability_catalog as cc
from espansr.core.command_catalog import LOCAL_ONLY_TEXT
from espansr.core.templates import (
    Template,
    TemplateManager,
    import_template,
    local_only_state,
    local_only_state_bytes,
    template_object,
)

ROOT = Path(__file__).resolve().parents[1]
BODY = '"name": "A", "content": "x", "trigger": ":a"'


def _deliver_module():
    spec = importlib.util.spec_from_file_location("deliver_rule", ROOT / "scripts" / "deliver.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CASES = {
    "absent": ("{" + BODY + "}").encode(),
    "false": ("{" + BODY + ', "local_only": false}').encode(),
    "true": ("{" + BODY + ', "local_only": true}').encode(),
    "string-true": ("{" + BODY + ', "local_only": "true"}').encode(),
    "one": ("{" + BODY + ', "local_only": 1}').encode(),
    "null": ("{" + BODY + ', "local_only": null}').encode(),
    "repeated": ("{" + BODY + ', "local_only": true, "local_only": false}').encode(),
    "repeated-false-first": ("{" + BODY + ', "local_only": false, "local_only": true}').encode(),
    "nested-only": ("{" + BODY + ', "variables": [{"name": "v", "local_only": true}]}').encode(),
    "bom-absent": b"\xef\xbb\xbf" + ("{" + BODY + "}").encode(),
    "bom-true": b"\xef\xbb\xbf" + ("{" + BODY + ', "local_only": true}').encode(),
    "utf16-false": ("{" + BODY + ', "local_only": false}').encode("utf-16"),
    "utf16-true": ("{" + BODY + ', "local_only": true}').encode("utf-16"),
    "broken-with-mark": ("{" + BODY + ', "local_only": true,}').encode(),
    "broken-without-mark": ("{" + BODY + ",}").encode(),
    # A byte that is not UTF-8: the review's shape, valid JSON once read as Latin-1.
    "not-utf8": b'{"name": "A", "content": "x\xff", "trigger": ":a"}',
    "not-utf8-false": b'{"name": "A", "content": "x\xff", "trigger": ":a", "local_only": false}',
    "not-utf8-with-mark": b'{"name": "A", "content": "x\xff", "trigger": ":a", "local_only": true}',
    "utf16-cut-true": ("{" + BODY + ', "local_only": true}').encode("utf-16") + b"\x00",
    "utf16-cut-absent": ("{" + BODY + "}").encode("utf-16") + b"\x00",
    "array": b"[1, 2]",
    "empty": b"",
}
EXPECTED = {
    "absent": "shareable",
    "false": "shareable",
    "nested-only": "shareable",
    "bom-absent": "shareable",
    "utf16-false": "shareable",
    "true": "private",
    "bom-true": "private",
    "utf16-true": "private",
    "broken-with-mark": "private",
    "not-utf8-with-mark": "private",
    "utf16-cut-true": "private",
}


@pytest.mark.parametrize("case", list(CASES))
def test_the_import_free_rule_matches_espansrs_own(case):
    raw = CASES[case]
    assert local_only_state_bytes(raw) == EXPECTED.get(case, "unknown")
    assert _deliver_module().local_only_state_bytes(raw) == local_only_state_bytes(raw)


@pytest.mark.parametrize("case", list(CASES))
def test_both_read_a_templates_identity_from_the_same_bytes(case):
    """Delivery and push recognize a private template under another name from these."""
    raw = CASES[case]
    assert _deliver_module().template_object(raw) == template_object(raw)
    if case.startswith(("not-utf8", "utf16-cut")):
        assert template_object(raw) is None  # bytes that do not decode are never read


def _flag_as_a_plain_reader_sees_it(path: Path):
    return json.loads(path.read_text(encoding="utf-8")).get("local_only")


def test_every_private_file_espansr_writes_carries_an_exact_flag(tmp_path):
    manager = TemplateManager(templates_dir=tmp_path / "live")
    diary = Template(name="Diary", content="v1", trigger=":diary", local_only=True)
    assert manager.save(diary)
    assert _flag_as_a_plain_reader_sees_it(diary._path) is True
    manager.create_version(diary, note="v1")
    assert manager.save_to_folder(diary, "personal")
    assert _flag_as_a_plain_reader_sees_it(diary._path) is True
    restored = manager.restore_version(diary, 1)
    assert _flag_as_a_plain_reader_sees_it(restored._path) is True
    incoming = tmp_path / "incoming" / "notes.json"
    incoming.parent.mkdir()
    incoming.write_text(
        json.dumps({"name": "Notes", "content": "x", "trigger": ":notes", "local_only": True}),
        encoding="utf-8",
    )
    imported = import_template(incoming, manager).template
    assert _flag_as_a_plain_reader_sees_it(imported._path) is True
    shared = Template(name="Shared", content="x", trigger=":shared")
    assert manager.save(shared)
    assert _flag_as_a_plain_reader_sees_it(shared._path) is None  # absent means shareable


REPEATED = (
    '{"name": "Notes", "content": "x", "trigger": ":notes", "local_only": true, '
    '"local_only": false}'
)


def test_a_repeated_local_only_loads_and_saves_as_private(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    (live / "notes.json").write_text(REPEATED, encoding="utf-8")
    manager = TemplateManager(templates_dir=live)

    [notes] = manager.list_all()
    assert notes.local_only is True
    notes.content = "edited"
    assert manager.save(notes)

    assert local_only_state(live / "notes.json") == "private"
    assert (live / "notes.json").read_text(encoding="utf-8").count('"local_only"') == 1


def test_an_imported_copy_of_a_repeated_local_only_stays_private(tmp_path):
    incoming = tmp_path / "incoming.json"
    incoming.write_text(REPEATED, encoding="utf-8")

    imported = import_template(incoming, TemplateManager(templates_dir=tmp_path / "live"))

    assert imported.template.local_only is True
    assert local_only_state(imported.template._path) == "private"


@pytest.fixture()
def publication(tmp_path):
    """A qualified publication that describes A and B."""
    source, live = tmp_path / "source", tmp_path / "live"
    for name in ("A", "B"):
        data = {"name": name, "content": f"{name} body", "trigger": f":{name.lower()}"}
        for root in (source, live):
            root.mkdir(exist_ok=True)
            (root / f"{name.lower()}.json").write_text(json.dumps(data), encoding="utf-8")
    assert cc.publish_catalog(source, live)["publication"] == "qualified"
    return source, live, live / cc.PUBLICATION_PATH


@pytest.mark.parametrize("write", ["save", "save_to_folder"])
def test_saving_a_template_as_local_only_withdraws_a_publication_that_describes_it(
    publication, write
):
    source, live, path = publication
    manager = TemplateManager(templates_dir=live)
    template = manager.load(live / "a.json")
    template.local_only = True

    assert getattr(manager, write)(template)  # no sync, no catalog read

    assert not path.exists()
    assert cc.inspect_catalog(source, live)["published"] is None


def test_saving_a_private_template_it_does_not_describe_keeps_the_publication(publication):
    _, live, path = publication
    before = path.read_bytes()

    assert TemplateManager(templates_dir=live).save(
        Template(name="Diary", content="x", trigger=":diary", local_only=True)
    )

    assert path.read_bytes() == before


def test_a_withdrawal_that_fails_at_save_is_reported_and_the_save_stands(
    publication, monkeypatch, capsys
):
    _, live, _ = publication
    monkeypatch.setattr(cc, "withdraw_private_publication", lambda *args: False)
    manager = TemplateManager(templates_dir=live)
    template = manager.load(live / "a.json")
    template.local_only = True

    assert manager.save(template)

    assert local_only_state(live / "a.json") == "private"
    out = capsys.readouterr().out
    assert "could not be removed" in out and "delete that file" in out


def test_the_catalog_withdraws_a_publication_once_its_template_repeats_local_only(publication):
    source, live, path = publication
    text = (live / "a.json").read_text(encoding="utf-8")
    (live / "a.json").write_text(
        text[:-1] + ', "local_only": true, "local_only": false}', encoding="utf-8"
    )

    result = cc.inspect_catalog(source, live)

    assert result["status"] == "withdrawn" and result["withdrawn_file_removed"]
    assert not path.exists()


def test_validate_warns_about_a_local_only_that_is_not_true_or_false():
    from espansr.core.config import get_templates_dir
    from espansr.integrations.validate import validate_all

    live = get_templates_dir()
    for name, value in (("Unclear", '"yes"'), ("Private", "true"), ("Open", "false")):
        (live / f"{name.lower()}.json").write_text(
            '{"name": "%s", "content": "x", "trigger": ":%s", "local_only": %s}'
            % (name, name.lower(), value),
            encoding="utf-8",
        )
    (live / "plain.json").write_text(
        '{"name": "Plain", "content": "x", "trigger": ":plain"}', encoding="utf-8"
    )

    flagged = [w for w in validate_all() if "local_only" in w.message]

    assert [(w.template_name, w.severity) for w in flagged] == [("Unclear", "warning")]
    assert "espansr keeps this prompt private" in flagged[0].message
    assert "other programs that read the file may not" in flagged[0].message


def test_the_local_only_note_never_promises_other_programs_cannot_read_it():
    assert "can still read it" in LOCAL_ONLY_TEXT
    assert "connected tools" not in LOCAL_ONLY_TEXT
