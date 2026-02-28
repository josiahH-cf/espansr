"""CLI entry point for espansr.

Commands:
  sync    — Sync templates to Espanso match file
  status  — Show Espanso process status and config path
  list    — Show templates with triggers
  setup   — Run post-install setup
  gui     — Launch the GUI
"""

import argparse
import shutil
import sys
from pathlib import Path

from espansr.core.config import get_config_dir, get_templates_dir
from espansr.integrations.espanso import (
    clean_stale_espanso_files,
    generate_launcher_file,
    get_espanso_config_dir,
)


def cmd_sync(args) -> int:
    """Sync all triggered templates to Espanso."""
    from espansr.integrations.espanso import sync_to_espanso

    success = sync_to_espanso()
    return 0 if success else 1


def _get_bundled_dir() -> Path:
    """Return the path to the repo-level bundled templates directory."""
    return Path(__file__).resolve().parent.parent / "templates"


def cmd_setup(args) -> int:
    """Run post-install setup: copy templates, detect Espanso, generate launcher."""
    get_config_dir()  # ensure config dir exists
    templates_dir = get_templates_dir()

    # ── Copy bundled templates (no-overwrite) ─────────────────────────────
    bundled_dir = _get_bundled_dir()
    copied = 0
    existing = 0
    if bundled_dir.is_dir():
        templates_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(bundled_dir.glob("*.json")):
            dest = templates_dir / src.name
            if dest.exists():
                existing += 1
            else:
                shutil.copy2(str(src), str(dest))
                copied += 1

    if copied:
        print(f"Templates: copied {copied} bundled template(s) to {templates_dir}")
    else:
        print(f"Templates: {templates_dir} ({existing} existing, no changes)")

    # ── Espanso detection and launcher ────────────────────────────────────
    espanso_dir = get_espanso_config_dir()
    if espanso_dir:
        clean_stale_espanso_files()
        generate_launcher_file()
        print(f"Espanso config: {espanso_dir}")
        print("Launcher: generated")
    else:
        from espansr.core.platform import get_platform

        plat = get_platform()
        if plat == "wsl2":
            print(
                "Espanso config: not found — install Espanso on Windows "
                "(https://espanso.org), then run 'espanso start' from PowerShell"
            )
        else:
            print(
                "Espanso config: not found — install Espanso "
                "(https://espanso.org), then run 'espanso start' to initialize"
            )
        print("Launcher: skipped (no Espanso config)")

    return 0


def cmd_status(args) -> int:
    """Show Espanso availability and config path."""
    from espansr.core.platform import is_wsl2

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
        print("Add a 'trigger' field (e.g. ':foo') to a template JSON to include it in sync.")
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
    subparsers.add_parser("validate", help="Validate templates for Espanso compatibility")
    subparsers.add_parser("setup", help="Run post-install setup")
    import_parser = subparsers.add_parser(
        "import", help="Import template(s) from a file or directory"
    )
    import_parser.add_argument("path", help="Path to a JSON file or directory of JSON files")
    subparsers.add_parser("gui", help="Launch the GUI")

    args = parser.parse_args()

    handlers = {
        "sync": cmd_sync,
        "status": cmd_status,
        "list": cmd_list,
        "validate": cmd_validate,
        "import": cmd_import,
        "setup": cmd_setup,
        "gui": cmd_gui,
    }

    if args.command in handlers:
        sys.exit(handlers[args.command](args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
