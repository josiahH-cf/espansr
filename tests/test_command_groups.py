"""Catalog coverage and identity guarantees for task-based command browsing."""

from pathlib import Path

from espansr.core.command_catalog import CommandCatalogEntry, build_command_catalog
from espansr.core.command_groups import COMMAND_GROUPS, CUSTOM_GROUP, command_cue, groups_for
from espansr.core.config import Config
from espansr.core.templates import Template, TemplateManager
from espansr.core.workflows import load_workflow_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_all_bundled_and_system_commands_have_curated_groups():
    manager = TemplateManager(templates_dir=ROOT / "templates")
    workflows = load_workflow_catalog([ROOT / "templates" / "_meta" / "workflows"])
    entries = build_command_catalog(manager, Config(), workflows)
    assert all(CUSTOM_GROUP not in groups_for(entry) for entry in entries)
    known = {entry.capability_id for entry in entries}
    assert {cap for group in COMMAND_GROUPS for cap in group.capabilities} == known
    assert {wid for group in COMMAND_GROUPS for wid in group.workflows} <= {
        workflow.id for workflow in workflows.workflows
    }
    assert all(command_cue(entry)[1] for entry in entries)


def test_context_and_litmus_belong_to_multiple_relevant_groups():
    def entry(capability):
        return CommandCatalogEntry(
            ":test", "Test", "description", "preview", "template", capability_id=capability
        )

    assert {g.id for g in groups_for(entry("context-reset"))} == {"keep-moving", "carry-context"}
    assert {g.id for g in groups_for(entry("human-litmus"))} == {"carry-context", "check-work"}
    moving = next(g for g in COMMAND_GROUPS if g.id == "keep-moving")
    assert {"continue", "unblock", "context-reset"} <= set(moving.capabilities)


def test_file_identity_and_membership_survive_trigger_and_display_name_changes(tmp_path):
    manager = TemplateManager(templates_dir=tmp_path)
    template = Template(name="Continue", trigger=":old", content="Continue this task.")
    manager.save(template)
    before = next(e for e in build_command_catalog(manager, Config()) if e.trigger == ":old")
    template.name = "My continuation"
    template.trigger = ":new"
    manager.save(template)
    after = next(e for e in build_command_catalog(manager, Config()) if e.trigger == ":new")
    assert before.capability_id == after.capability_id == "continue"
    assert groups_for(before) == groups_for(after)


def test_custom_commands_keep_live_guidance_without_forced_category_mapping():
    entry = CommandCatalogEntry(
        ":mine",
        "My command",
        "My description",
        "preview",
        "template",
        category="workflow",
        capability_id="my-custom-job",
        use_when="My real use case.",
    )
    assert groups_for(entry) == (CUSTOM_GROUP,)
    assert command_cue(entry) == ("workflow", "My real use case.")


def test_system_membership_survives_configurable_trigger_renames(tmp_path):
    config = Config()
    config.espanso.launcher_trigger = ":editor"
    config.espanso.sync_trigger = ":update"
    entries = build_command_catalog(TemplateManager(templates_dir=tmp_path), config)
    assert {entry.capability_id for entry in entries} == {
        "espansr-launcher",
        "espansr-commands",
        "espansr-sync",
    }
    assert all(groups_for(entry)[0].id == "tools-setup" for entry in entries)
