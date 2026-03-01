"""Tests for shell tab completion.

Covers: ``espansr completions bash``, ``espansr completions zsh``,
subcommand/flag content in generated scripts, argparse-driven generation,
and help registration.
"""

import argparse
import sys
from unittest.mock import patch


# Expected subcommands from the current parser (alphabetical for assertions)
EXPECTED_SUBCOMMANDS = sorted(
    ["sync", "status", "list", "validate", "import", "setup", "doctor", "gui", "completions"]
)


# ── bash output ───────────────────────────────────────────────────────────────


def test_completions_bash_prints_script(capsys):
    """``espansr completions bash`` prints a non-empty bash script to stdout."""
    from espansr.__main__ import cmd_completions

    args = argparse.Namespace(shell="bash")
    exit_code = cmd_completions(args)

    out = capsys.readouterr().out
    assert exit_code == 0
    assert out.strip(), "bash completion script must not be empty"
    # Should look like a bash script
    assert "_espansr" in out or "complete" in out


def test_bash_script_contains_subcommands(capsys):
    """Bash completion script lists every registered subcommand."""
    from espansr.__main__ import cmd_completions

    args = argparse.Namespace(shell="bash")
    cmd_completions(args)
    out = capsys.readouterr().out

    for cmd in EXPECTED_SUBCOMMANDS:
        assert cmd in out, f"bash script missing subcommand: {cmd}"


def test_bash_script_contains_top_level_flags(capsys):
    """Bash completion script contains --version and --help."""
    from espansr.__main__ import cmd_completions

    args = argparse.Namespace(shell="bash")
    cmd_completions(args)
    out = capsys.readouterr().out

    assert "--version" in out
    assert "--help" in out


# ── zsh output ────────────────────────────────────────────────────────────────


def test_completions_zsh_prints_script(capsys):
    """``espansr completions zsh`` prints a non-empty zsh script to stdout."""
    from espansr.__main__ import cmd_completions

    args = argparse.Namespace(shell="zsh")
    exit_code = cmd_completions(args)

    out = capsys.readouterr().out
    assert exit_code == 0
    assert out.strip(), "zsh completion script must not be empty"
    assert "_espansr" in out or "compadd" in out


def test_zsh_script_contains_subcommands(capsys):
    """Zsh completion script lists every registered subcommand."""
    from espansr.__main__ import cmd_completions

    args = argparse.Namespace(shell="zsh")
    cmd_completions(args)
    out = capsys.readouterr().out

    for cmd in EXPECTED_SUBCOMMANDS:
        assert cmd in out, f"zsh script missing subcommand: {cmd}"


def test_zsh_script_contains_top_level_flags(capsys):
    """Zsh completion script contains --version and --help."""
    from espansr.__main__ import cmd_completions

    args = argparse.Namespace(shell="zsh")
    cmd_completions(args)
    out = capsys.readouterr().out

    assert "--version" in out
    assert "--help" in out


# ── argparse-driven generation ────────────────────────────────────────────────


def test_completions_generated_from_parser():
    """Completion output reflects argparse state, not a hardcoded list.

    Adds a temporary subparser and verifies it appears in the generated script.
    """
    from espansr.core.completions import build_bash_completion

    parser = argparse.ArgumentParser(prog="espansr")
    subs = parser.add_subparsers(dest="command")
    subs.add_parser("alpha")
    subs.add_parser("beta")

    script = build_bash_completion(parser)
    assert "alpha" in script
    assert "beta" in script
    # A command NOT registered must be absent
    assert "gamma" not in script


# ── help registration ────────────────────────────────────────────────────────


def test_completions_in_help(capsys):
    """``completions`` appears in top-level ``--help`` output."""
    from espansr.__main__ import main

    with patch.object(sys, "argv", ["espansr", "--help"]):
        try:
            main()
        except SystemExit:
            pass

    out = capsys.readouterr().out
    assert "completions" in out
