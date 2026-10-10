"""The repeatable delivery loop is written where every model reads it.

AGENTS.md is the instruction surface for every client, CLAUDE.md carries the
Claude-specific delivery authorization, and scripts/deliver.py is the one
delivery route both name. Dropping any of these lets a model fall back to its
own interpretation of "go" or "reinstall", which is how deliveries drifted.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def test_agents_defines_reinstall_as_refresh():
    assert '"Reinstall" means `espansr refresh`' in AGENTS
    assert "`espansr publish` only re-syncs templates to Espanso and is not a reinstall." in AGENTS
    assert "`Espanso process: running independently`" in AGENTS


def test_agents_defines_the_template_delivery_loop():
    for phrase in (
        "## Template Delivery Loop",
        "When no change is named yet, ask what to change and wait.",
        "ask one consolidated batch of questions with a recommended answer for each",
        '"Go", "do it", or "approve" authorizes everything below without further questions',
        "python scripts/deliver.py --branch agent/<type>-<short-name>",
        "List every file you changed.",
        "After two failed attempts at the same stage, report the blocker",
        "Then ask for the next change.",
        "Never revert, stash, or commit changes you did not make",
        "never actual values such as amounts, account digits, dates, or private names",
        "codex -s danger-full-access -a never",
        "never merge with `--admin`",
    ):
        assert phrase in AGENTS, phrase


def test_claude_authorizes_unattended_delivery_through_the_script():
    for phrase in (
        "## Unattended Delivery",
        'After "go", run `python scripts/deliver.py ...` without asking',
        "Run it with `run_in_background`",
        "`deliver.py` is the only wait for CI",
    ):
        assert phrase in CLAUDE, phrase


def test_delivery_script_reinstalls_with_refresh():
    script = (ROOT / "scripts" / "deliver.py").read_text(encoding="utf-8")
    assert '"-m", "espansr", "refresh"' in script
    assert '"publish"' not in script
    assert "--admin" not in script
