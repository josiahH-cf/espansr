"""CLI entry point for automatr-espanso.

Commands:
  sync    — Sync templates to Espanso match file
  status  — Show Espanso process status and config path
  list    — Show templates with triggers
  gui     — Launch the GUI
"""

import argparse
import sys


def cmd_sync(args) -> int:
    """Sync all triggered templates to Espanso."""
    from automatr_espanso.integrations.espanso import sync_to_espanso

    success = sync_to_espanso()
    return 0 if success else 1


def cmd_status(args) -> int:
    """Show Espanso availability and config path."""
    import shutil

    from automatr_espanso.core.platform import is_wsl2
    from automatr_espanso.integrations.espanso import get_espanso_config_dir

    config_dir = get_espanso_config_dir()
    if config_dir:
        print(f"Espanso config: {config_dir}")
    else:
        print("Espanso config: not found")

    # Check for native binary
    espanso_bin = shutil.which("espanso")
    if espanso_bin:
        print(f"Espanso binary: {espanso_bin}")
        return 0

    # WSL2: Espanso runs on the Windows side
    if is_wsl2():
        print("Espanso binary: Windows host (WSL2 — use PowerShell to manage)")
    else:
        print("Espanso binary: not found")

    return 0


def cmd_list(args) -> int:
    """List templates that have triggers defined."""
    from automatr_espanso.core.templates import get_template_manager

    manager = get_template_manager()
    triggered = list(manager.iter_with_triggers())

    if not triggered:
        print("No templates with triggers found.")
        print(
            "Add a 'trigger' field (e.g. ':foo') to a template JSON to include it in sync."
        )
        return 0

    print(f"{'TRIGGER':<22} TEMPLATE NAME")
    print("-" * 60)
    for t in triggered:
        print(f"  {t.trigger:<20} {t.name}")

    return 0


def cmd_gui(args) -> int:
    """Launch the PyQt6 GUI."""
    from automatr_espanso.ui.main_window import launch

    launch()
    return 0


def main() -> None:
    """Entry point for the automatr-espanso CLI."""
    parser = argparse.ArgumentParser(
        prog="automatr-espanso",
        description="Espanso text expansion template manager",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    subparsers.add_parser("sync", help="Sync templates to Espanso match file")
    subparsers.add_parser("status", help="Show Espanso process status and config path")
    subparsers.add_parser("list", help="List templates with triggers")
    subparsers.add_parser("gui", help="Launch the GUI")

    args = parser.parse_args()

    handlers = {
        "sync": cmd_sync,
        "status": cmd_status,
        "list": cmd_list,
        "gui": cmd_gui,
    }

    if args.command in handlers:
        sys.exit(handlers[args.command](args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
