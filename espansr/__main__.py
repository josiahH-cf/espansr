"""CLI entry point for espansr.

Commands:
  sync    — Sync templates to Espanso match file
  status  — Show Espanso process status and config path
  list    — Show templates with triggers
  setup   — Run post-install setup
  doctor  — Run diagnostic health checks
  gui     — Launch the GUI
"""

import argparse
import shutil
import sys
from pathlib import Path

from espansr.core.cli_color import fail, ok, warn
from espansr.core.config import get_config_dir, get_templates_dir
from espansr.core.platform import get_platform
from espansr.integrations.espanso import (
    clean_stale_espanso_files,
    generate_launcher_file,
    get_espanso_config_dir,
)


def cmd_sync(args) -> int:
    """Sync all triggered templates to Espanso."""
    from espansr.integrations.espanso import sync_to_espanso

    dry_run = getattr(args, "dry_run", False) if args else False
    success = sync_to_espanso(dry_run=dry_run)
    return 0 if success else 1


def _get_bundled_dir() -> Path:
    """Return the path to the bundled templates directory.

    Prefers the repo-level ``templates/`` directory (editable installs).
    Falls back to ``importlib.resources`` for non-editable installs.
    """
    repo_level = Path(__file__).resolve().parent.parent / "templates"
    if repo_level.is_dir():
        return repo_level

    # Fallback: package data via importlib.resources (Python 3.11+)
    from importlib.resources import files

    pkg_path = files("espansr").joinpath("..", "templates")
    return Path(str(pkg_path))


def cmd_setup(args) -> int:
    """Run post-install setup: copy templates, detect Espanso, generate launcher.

    With ``--strict``, returns 1 if Espanso config is not detected.
    With ``--dry-run``, previews actions without making changes.
    With ``--verbose``, prints per-file detail during template copy.
    After copying templates, validates each one and prints any issues.
    """
    from espansr.core.templates import TemplateManager
    from espansr.integrations.validate import validate_template

    strict = getattr(args, "strict", False) if args else False
    dry_run = getattr(args, "dry_run", False) if args else False
    verbose = getattr(args, "verbose", False) if args else False

    get_config_dir()  # ensure config dir exists
    templates_dir = get_templates_dir()

    # ── Copy bundled templates (no-overwrite) ─────────────────────────────
    bundled_dir = _get_bundled_dir()
    copied = 0
    existing = 0
    if bundled_dir.is_dir():
        if not dry_run:
            templates_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(bundled_dir.glob("*.json")):
            dest = templates_dir / src.name
            if dest.exists():
                existing += 1
                if verbose or dry_run:
                    print(f"  {src.name}: skipped (already exists)")
            else:
                if dry_run:
                    if verbose:
                        print(f"  {src.name}: would copy")
                    copied += 1
                else:
                    shutil.copy2(str(src), str(dest))
                    copied += 1
                    if verbose:
                        print(f"  {src.name}: copied")

    prefix = "[dry-run] " if dry_run else ""
    if dry_run:
        if copied:
            print(f"{prefix}Would copy {copied} bundled template(s) to {templates_dir}")
        else:
            print(f"{prefix}Templates: {templates_dir} ({existing} existing, no changes)")
    elif copied:
        print(f"Templates: copied {copied} bundled template(s) to {templates_dir}")
    else:
        print(f"Templates: {templates_dir} ({existing} existing, no changes)")

    # ── Validate copied templates ─────────────────────────────────────────
    if not dry_run:
        mgr = TemplateManager(templates_dir=templates_dir)
        all_warnings = []
        for template in mgr.iter_with_triggers():
            all_warnings.extend(validate_template(template))

        errors = [w for w in all_warnings if w.severity == "error"]
        non_errors = [w for w in all_warnings if w.severity != "error"]

        for w in non_errors:
            print(f"Validation: Warning [{w.template_name}]: {w.message}")
        for w in errors:
            print(f"Validation: Error [{w.template_name}]: {w.message}")
        if not all_warnings:
            print("Validation: all templates valid")

    # ── Espanso detection and launcher ────────────────────────────────────
    espanso_dir = get_espanso_config_dir()
    espanso_found = bool(espanso_dir)
    if espanso_dir:
        if dry_run:
            print(f"[dry-run] Would detect Espanso config: {espanso_dir}")
            print("[dry-run] Would generate launcher")
        else:
            clean_stale_espanso_files()
            generate_launcher_file()
            print(f"Espanso config: {espanso_dir}")
            print("Launcher: generated")
    else:
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

    # ── orchestratr manifest ──────────────────────────────────────────────
    if not dry_run:
        from espansr.integrations.orchestratr import (
            generate_manifest,
            manifest_needs_update,
        )

        config_dir_path = get_config_dir()
        if manifest_needs_update(config_dir_path):
            manifest_path = generate_manifest(config_dir_path)
            print(f"orchestratr manifest: written to {manifest_path}")
        else:
            print("orchestratr manifest: up to date")
    else:
        print("[dry-run] Would check/regenerate orchestratr manifest")

    if strict and not espanso_found:
        return 1
    return 0


def cmd_status(args) -> int:
    """Show Espanso availability and config path.

    With ``--json``, outputs machine-readable JSON status for orchestratr
    health checks instead of human-readable text.
    """
    if getattr(args, "json", False):
        from espansr.integrations.orchestratr import get_status_json

        print(get_status_json())
        return 0

    config_dir = get_espanso_config_dir()
    if config_dir:
        print(ok(f"Espanso config: {config_dir}"))
    else:
        platform = get_platform()
        if platform == "wsl2":
            print(
                fail(
                    "Espanso config: not found \u2014 install Espanso on Windows"
                    " (https://espanso.org), then run 'espanso start' from PowerShell"
                )
            )
        else:
            print(
                fail(
                    "Espanso config: not found \u2014 install Espanso"
                    " (https://espanso.org), then run 'espanso start' to initialize"
                )
            )

    # Check for native binary
    espanso_bin = shutil.which("espanso")
    if espanso_bin:
        print(ok(f"Espanso binary: {espanso_bin}"))
        return 0

    # WSL2: Espanso runs on the Windows side
    if get_platform() == "wsl2":
        print(warn("Espanso binary: Windows host (WSL2 — use PowerShell to manage)"))
    else:
        print(fail("Espanso binary: not found"))

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
        print(warn(f"[{w.template_name}]: {w.message}"))
    for w in errors:
        print(fail(f"[{w.template_name}]: {w.message}"))

    if not warnings:
        print(ok("All templates valid."))

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


def cmd_doctor(args) -> int:
    """Run diagnostic health checks and print a consolidated report.

    Checks Python version, config dir, templates, Espanso config,
    Espanso binary, launcher file, and template validation.
    Returns 0 if no checks fail, 1 if any check is [FAIL].
    """
    from espansr.core.templates import get_template_manager
    from espansr.integrations.espanso import get_match_dir
    from espansr.integrations.validate import validate_all

    has_fail = False

    def _ok(msg: str) -> None:
        print(ok(msg))

    def _warn(msg: str) -> None:
        print(warn(msg))

    def _fail(msg: str) -> None:
        nonlocal has_fail
        has_fail = True
        print(fail(msg))

    # 1. Python version
    ver = sys.version_info
    if ver >= (3, 11):
        _ok(f"Python {ver.major}.{ver.minor}.{ver.micro}")
    else:
        _fail(f"Python {ver.major}.{ver.minor}.{ver.micro} (3.11+ required)")

    # 2. espansr config dir
    config_dir = get_config_dir()
    if config_dir.is_dir():
        _ok(f"Config dir: {config_dir}")
    else:
        _fail(f"Config dir not found: {config_dir}")

    # 3. Templates found
    manager = get_template_manager()
    triggered = list(manager.iter_with_triggers())
    if triggered:
        _ok(f"Templates: {len(triggered)} with triggers")
    else:
        _fail("No templates with triggers found")

    # 4. Espanso config detected
    espanso_dir = get_espanso_config_dir()
    if espanso_dir:
        _ok(f"Espanso config: {espanso_dir}")
    else:
        _fail("Espanso config: not found")

    # 5. Espanso binary
    espanso_bin = shutil.which("espanso")
    platform = get_platform()
    if espanso_bin:
        _ok(f"Espanso binary: {espanso_bin}")
    elif platform == "wsl2":
        _ok("Espanso binary: Windows host (WSL2)")
    else:
        _fail("Espanso binary: not found")

    # 6. Launcher file
    match_dir = get_match_dir()
    if match_dir and (match_dir / "espansr-launcher.yml").exists():
        _ok("Launcher: espansr-launcher.yml present")
    else:
        _fail("Launcher: espansr-launcher.yml not found")

    # 7. Template validation
    warnings = validate_all()
    errors = [w for w in warnings if w.severity == "error"]
    non_errors = [w for w in warnings if w.severity != "error"]
    if errors:
        _fail(f"Validation: {len(errors)} error(s)")
    elif non_errors:
        _warn(f"Validation: {len(non_errors)} warning(s)")
    else:
        _ok("Validation: all templates valid")

    return 1 if has_fail else 0


def cmd_completions(args) -> int:
    """Print a shell completion script to stdout."""
    from espansr.core.completions import build_bash_completion, build_zsh_completion

    # Build a parser identical to the real one so the script reflects all commands.
    parser = _build_parser()
    if args.shell == "bash":
        print(build_bash_completion(parser))
    elif args.shell == "zsh":
        print(build_zsh_completion(parser))
    return 0


def cmd_gui(args) -> int:
    """Launch the PyQt6 GUI."""
    from espansr.ui.main_window import launch

    launch()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the full CLI argument parser."""
    from espansr import __version__

    parser = argparse.ArgumentParser(
        prog="espansr",
        description="Espanso text expansion template manager",
    )
    parser.add_argument("--version", action="version", version=f"espansr {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    sync_parser = subparsers.add_parser("sync", help="Sync templates to Espanso match file")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview what would be synced without writing any files",
    )
    status_parser = subparsers.add_parser(
        "status", help="Show Espanso process status and config path"
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output machine-readable JSON status for orchestratr",
    )
    subparsers.add_parser("list", help="List templates with triggers")
    subparsers.add_parser("validate", help="Validate templates for Espanso compatibility")
    setup_parser = subparsers.add_parser("setup", help="Run post-install setup")
    setup_parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Return exit code 1 if Espanso config is not detected",
    )
    setup_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview what setup would do without making changes",
    )
    setup_parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print detailed per-file information during setup",
    )
    subparsers.add_parser("doctor", help="Run diagnostic health checks")
    import_parser = subparsers.add_parser(
        "import", help="Import template(s) from a file or directory"
    )
    import_parser.add_argument("path", help="Path to a JSON file or directory of JSON files")
    subparsers.add_parser("gui", help="Launch the GUI")
    comp_parser = subparsers.add_parser(
        "completions", help="Print shell completion script"
    )
    comp_parser.add_argument(
        "shell",
        choices=["bash", "zsh"],
        help="Target shell (bash or zsh)",
    )

    return parser


def main() -> None:
    """Entry point for the espansr CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    handlers = {
        "sync": cmd_sync,
        "status": cmd_status,
        "list": cmd_list,
        "validate": cmd_validate,
        "import": cmd_import,
        "setup": cmd_setup,
        "doctor": cmd_doctor,
        "gui": cmd_gui,
        "completions": cmd_completions,
    }

    if args.command in handlers:
        sys.exit(handlers[args.command](args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
