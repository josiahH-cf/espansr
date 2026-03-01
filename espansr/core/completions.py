"""Shell completion script generators for espansr.

Generates bash and zsh completion scripts by introspecting the argparse
parser, so the command list stays in sync automatically as subcommands
are added or removed.
"""

from __future__ import annotations

import argparse
from typing import List


def _extract_subcommands(parser: argparse.ArgumentParser) -> List[str]:
    """Return the list of subcommand names registered on *parser*."""
    for action in parser._subparsers._actions:
        if isinstance(action, argparse._SubParsersAction):
            return sorted(action.choices.keys())
    return []


def _extract_top_level_flags(parser: argparse.ArgumentParser) -> List[str]:
    """Return top-level optional flags (e.g. ``--help``, ``--version``)."""
    flags: List[str] = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            continue
        for opt in action.option_strings:
            if opt.startswith("--"):
                flags.append(opt)
    return sorted(flags)


def build_bash_completion(parser: argparse.ArgumentParser) -> str:
    """Generate a bash completion script from *parser*.

    The script completes subcommand names and top-level flags when the
    user types ``espansr <TAB>``.
    """
    commands = _extract_subcommands(parser)
    flags = _extract_top_level_flags(parser)
    words = " ".join(commands + flags)

    return f"""\
_espansr() {{
    local cur commands
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    commands="{words}"

    if [[ ${{COMP_CWORD}} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${{commands}}" -- "${{cur}}") )
    fi
}}

complete -F _espansr espansr
"""


def build_zsh_completion(parser: argparse.ArgumentParser) -> str:
    """Generate a zsh completion script from *parser*.

    The script completes subcommand names and top-level flags when the
    user types ``espansr <TAB>``.
    """
    commands = _extract_subcommands(parser)
    flags = _extract_top_level_flags(parser)
    words = " ".join(commands + flags)

    return f"""\
#compdef espansr

_espansr() {{
    local -a commands
    commands=({words})
    _describe 'command' commands
    compadd -- ${{commands[@]}}
}}

compdef _espansr espansr
"""
