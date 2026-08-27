"""GUI acceptance checks for capability metadata authoring (ARCH-09).

The template editor exposes the capability metadata in a collapsible optional
section, simple editing stays simple (the section starts collapsed), saving
preserves the metadata, and the browser can find templates by it.
"""

from unittest.mock import patch

import pytest

from espansr.core.templates import Template, TemplateManager

pytest.importorskip("PyQt6")


@pytest.fixture()
def tm(tmp_path):
    return TemplateManager(templates_dir=tmp_path)


@pytest.fixture()
def _patch_tm(tm):
    with (
        patch("espansr.ui.template_editor.get_template_manager", return_value=tm),
        patch("espansr.ui.template_editor.get_config"),
    ):
        yield


@pytest.fixture()
def editor(qtbot, _patch_tm):
    from espansr.ui.template_editor import TemplateEditorWidget

    widget = TemplateEditorWidget()
    qtbot.addWidget(widget)
    return widget


def _capability_template():
    return Template(
        name="Cap Template",
        content="body",
        trigger=":captest",
        capability_id="cap-test",
        intent_tags=["first tag", "second tag"],
        accepts=["evidence-report"],
        produces=["gap-review"],
        use_when="use it now",
        avoid_when="avoid it later",
        output_contract={"schema": 1, "required_sections": ["A"]},
    )


# ── Collapsible section keeps simple editing simple ──────────────────────────


def test_metadata_section_exists_and_starts_collapsed(editor):
    assert hasattr(editor, "_metadata_container")
    assert hasattr(editor, "_metadata_toggle")
    assert not editor._metadata_container.isVisibleTo(editor)


def test_metadata_toggle_shows_section(editor):
    editor._metadata_toggle.setChecked(True)
    assert editor._metadata_container.isVisibleTo(editor)
    editor._metadata_toggle.setChecked(False)
    assert not editor._metadata_container.isVisibleTo(editor)


# ── Load / clear / save round-trip ───────────────────────────────────────────


def test_loading_template_populates_metadata_fields(editor):
    editor.load_template(_capability_template())
    assert editor._capability_id_edit.text() == "cap-test"
    assert editor._intent_tags_edit.text() == "first tag, second tag"
    assert editor._accepts_edit.text() == "evidence-report"
    assert editor._produces_edit.text() == "gap-review"
    assert editor._use_when_edit.text() == "use it now"
    assert editor._avoid_when_edit.text() == "avoid it later"


def test_clear_resets_metadata_fields(editor):
    editor.load_template(_capability_template())
    editor.clear()
    assert editor._capability_id_edit.text() == ""
    assert editor._intent_tags_edit.text() == ""


def test_saving_preserves_metadata(editor, tm):
    editor.load_template(_capability_template())
    editor.save_current(emit_signal=False)

    loaded = tm.get("Cap Template")
    assert loaded is not None
    assert loaded.capability_id == "cap-test"
    assert loaded.intent_tags == ["first tag", "second tag"]
    assert loaded.accepts == ["evidence-report"]
    assert loaded.produces == ["gap-review"]
    assert loaded.use_when == "use it now"
    assert loaded.avoid_when == "avoid it later"
    # The output contract has no editor UI but must survive a GUI save.
    assert loaded.output_contract == {"schema": 1, "required_sections": ["A"]}


def test_editing_metadata_marks_unsaved_changes(editor):
    editor.load_template(_capability_template())
    assert not editor.has_unsaved_changes()
    editor._intent_tags_edit.setText("changed tag")
    assert editor.has_unsaved_changes()


def test_new_template_with_metadata_saves_it(editor, tm):
    editor._name_edit.setText("Fresh Cap")
    editor._trigger_edit.setText(":freshcap")
    editor._content_edit.setPlainText("body")
    editor._capability_id_edit.setText("fresh-cap")
    editor._use_when_edit.setText("brand new")
    editor.save_current(emit_signal=False)

    loaded = tm.get("Fresh Cap")
    assert loaded is not None
    assert loaded.capability_id == "fresh-cap"
    assert loaded.use_when == "brand new"


def test_simple_template_editing_stays_simple(editor, tm):
    """A plain template saves without metadata fields inventing values."""
    editor._name_edit.setText("Plain")
    editor._trigger_edit.setText(":plain")
    editor._content_edit.setPlainText("plain body")
    editor.save_current(emit_signal=False)
    loaded = tm.get("Plain")
    assert loaded is not None
    assert loaded.capability_id == ""
    assert loaded.intent_tags == []
    assert loaded.output_contract == {}


# ── Browser search covers capability metadata ────────────────────────────────


def test_browser_search_matches_intent_tags(qtbot, tmp_path):
    manager = TemplateManager(templates_dir=tmp_path)
    manager.save(_capability_template())
    manager.save(Template(name="Other", content="x", trigger=":other"))

    with (
        patch("espansr.ui.template_browser.get_template_manager", return_value=manager),
        patch("espansr.ui.template_browser.get_config"),
    ):
        from espansr.ui.template_browser import TemplateBrowserWidget

        browser = TemplateBrowserWidget()
        qtbot.addWidget(browser)
        browser.load_templates()

        matched = browser._filter_templates("second tag")
        assert [t.name for t in matched] == ["Cap Template"]
        matched = browser._filter_templates("cap-test")
        assert [t.name for t in matched] == ["Cap Template"]
