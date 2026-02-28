"""CLI entry point for espansr.

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
    from espansr.integrations.espanso import sync_to_espanso

    success = sync_to_espanso()
    return 0 if success else 1


def cmd_status(args) -> int:
    """Show Espanso availability and config path."""
    import shutil

    from espansr.core.platform import is_wsl2
    from espansr.integrations.espanso import get_espanso_config_dir

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
    from espansr.core.templates import get_template_manager

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


def cmd_validate(args) -> int:
    """Validate templates for Espanso compatibility."""
    from espansr.integrations.validate import validate_all

    warnings = validate_all()
    errors = [w for w in warnings if w.severity == "error"]
    non_errors = [w for w in warnings if w.severity != "error"]

    for w in non_errors:
        print(f"Warning [{w.template_name}]: {w.message}")
    for w in errors:
        print(f"Error [{w.template_name}]: {w.message}")

    if not warnings:
        print("All templates valid.")

    return 1 if errors else 0


def cmd_import(args) -> int:
    """Import template JSON file(s) from an external path."""
    from pathlib import Path

    from espansr.core.templates import import_template, import_templates

    target = Path(args.path)

    if target.is_dir():
        summary = import_templates(target)
        if summary.error:
            print(f"Error: {summary.error}")
            return 1
        print(f"Imported {summary.succeeded} template(s), {summary.failed} failed.")
        for r in summary.results:
            if r.template:
                suffix = " (renamed)" if r.renamed else ""
                print(f"  + {r.template.name}{suffix}")
            elif r.error:
                print(f"  ! {r.error}")
        return 1 if summary.failed and summary.succeeded == 0 else 0

    if target.is_file():
        result = import_template(target)
        if result.template:
            suffix = " (renamed)" if result.renamed else ""
            print(f"Imported 1 template: {result.template.name}{suffix}")
            return 0
        else:
            print(f"Error: {result.error}")
            return 1

    print(f"Error: path not found: {target}")
    return 1


def cmd_gui(args) -> int:
    """Launch the PyQt6 GUI."""
    from espansr.ui.main_window import launch

    launch()
    return 0


def main() -> None:
    """Entry point for the espansr CLI."""
    parser = argparse.ArgumentParser(
        prog="espansr",
        description="Espanso text expansion template manager",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    subparsers.add_parser("sync", help="Sync templates to Espanso match file")
    subparsers.add_parser("status", help="Show Espanso process status and config path")
    subparsers.add_parser("list", help="List templates with triggers")
    subparsers.add_parser(
        "validate", help="Validate templates for Espanso compatibility"
    )
    import_parser = subparsers.add_parser(
        "import", help="Import template(s) from a file or directory"
    )
    import_parser.add_argument(
        "path", help="Path to a JSON file or directory of JSON files"
    )
    subparsers.add_parser("gui", help="Launch the GUI")

    args = parser.parse_args()

    handlers = {
        "sync": cmd_sync,
        "status": cmd_status,
        "list": cmd_list,
        "validate": cmd_validate,
        "import": cmd_import,
        "gui": cmd_gui,
    }

    if args.command in handlers:
        sys.exit(handlers[args.command](args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
