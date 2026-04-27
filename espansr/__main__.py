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
import subprocess
import sys
from pathlib import Path

from espansr.core.cli_color import fail, ok, warn
from espansr.core.config import get_config_dir, get_templates_dir
from espansr.core.platform import get_platform
from espansr.integrations.espanso import (
    _get_candidate_paths,
    clean_stale_espanso_files,
    generate_commands_popup_file,
    generate_launcher_file,
    get_espanso_config_dir,
)


def _print_wsl_espanso_remediation() -> None:
    """Print copy/paste-ready WSL steps for missing Espanso dependency."""
    print("WSL2 note: Windows PowerShell and WSL are separate environments.")
    print(
        "If you want a native Windows-hosted espansr install, "
        "run .\\install.ps1 in Windows PowerShell."
    )
    print("WSL2 note: espansr does not install Espanso automatically.")
    print("Recommended: run the wrapper from WSL:")
    print("  espansr wsl-install-espanso")
    print("Or run manually in Windows PowerShell:")
    print(
        "  winget install --id Espanso.Espanso -e "
        "--accept-package-agreements --accept-source-agreements"
    )
    print("  espanso start")
    print("Then re-check from WSL:")
    print("  espansr doctor")


def _print_wsl_install_action_required() -> None:
    """Print minimal checklist when wrapper cannot verify a complete install."""
    print("Action required in Windows:")
    print("  1. If installer UI opened, complete the Espanso .exe wizard")
    print("  2. Open a new PowerShell window")
    print("  3. Run: espanso start")
    print("  4. Return to WSL and run: espansr doctor")


def cmd_wsl_install_espanso(args) -> int:
    """Install and start Espanso on Windows host from WSL.

    This command is WSL2-only. It uses PowerShell to install Espanso via winget,
    then attempts to start Espanso using known executable locations to handle
    PATH/session lag after install. It manages Windows-side Espanso only;
    Windows PowerShell and WSL remain separate espansr environments.
    """
    if get_platform() != "wsl2":
        print(fail("wsl-install-espanso is only supported when running inside WSL2"))
        return 1

    script = r"""
$ErrorActionPreference = 'Continue'

$installOk = $true
try {
    winget install --id Espanso.Espanso -e --accept-package-agreements --accept-source-agreements
} catch {
    $installOk = $false
}

$candidates = @(
    "$Env:LOCALAPPDATA\Programs\Espanso\espanso.exe",
    "$Env:LOCALAPPDATA\Programs\espanso\espanso.exe",
    "$Env:ProgramFiles\Espanso\espanso.exe",
    "$Env:ProgramFiles(x86)\Espanso\espanso.exe",
    "$Env:LOCALAPPDATA\Microsoft\WindowsApps\espanso.exe"
)

$espansoExe = $null
foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
        $espansoExe = $candidate
        break
    }
}

if (-not $espansoExe) {
    $cmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($cmd) {
        $espansoExe = $cmd.Source
    }
}

if (-not $espansoExe) {
    Write-Host "ACTION_REQUIRED: Espanso executable not detected in this PowerShell session."
    if (-not $installOk) {
        Write-Host "winget did not report a clean install. Complete the .exe installer if prompted."
    }
    exit 2
}

$startOk = $true
try {
    & $espansoExe start
} catch {
    $startOk = $false
}

$configCandidates = @(
    "$Env:APPDATA\espanso",
    "$Env:USERPROFILE\.config\espanso"
)
$configDetected = $false
foreach ($cfg in $configCandidates) {
    if (Test-Path $cfg) {
        $configDetected = $true
        break
    }
}

if (-not $startOk -or -not $configDetected) {
    Write-Host "ACTION_REQUIRED: Install may be partial; startup/config verification did not pass."
    if (-not $configDetected) {
        Write-Host "Espanso config directory was not detected yet."
    }
    exit 2
}

& $espansoExe status
exit 0
"""

    print("Running Windows-side Espanso install/start from WSL...")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        text=True,
        check=False,
    )

    if completed.returncode == 0:
        print(ok("Espanso install/start wrapper completed with verification"))
        print("Next: run `espansr doctor` and `espansr setup` from WSL")
        return 0

    if completed.returncode == 2:
        print(warn("Espanso install wrapper finished with ACTION REQUIRED."))
        _print_wsl_install_action_required()
        return 1

    print(fail(f"PowerShell wrapper failed with exit code {completed.returncode}"))
    return 1


def _auto_pull_if_configured() -> None:
    """Run auto-pull silently if a remote is configured."""
    try:
        from espansr.core.remote import RemoteManager

        rm = RemoteManager()
        rm.auto_pull()
    except Exception:
        pass  # auto-pull failures are non-blocking


def cmd_sync(args) -> int:
    """Sync all triggered templates to Espanso."""
    from espansr.integrations.espanso import sync_to_espanso

    _auto_pull_if_configured()
    dry_run = getattr(args, "dry_run", False) if args else False
    success = sync_to_espanso(
        dry_run=dry_run,
        update_bundled=True,
        bundled_dir=_get_bundled_dir(),
    )
    return 0 if success else 1


def _get_bundled_dir() -> Path:
    """Return the path to the bundled templates directory.

    Prefers the repo-level ``templates/`` directory (editable installs).
    Falls back to ``importlib.resources`` for non-editable installs.
    """
    from espansr.core.templates import get_bundled_templates_dir

    return get_bundled_templates_dir(__file__)


def cmd_setup(args) -> int:
    """Run post-install setup: copy templates, detect Espanso, sync, and generate launcher.

    With ``--strict``, returns 1 if Espanso config is not detected.
    With ``--dry-run``, previews actions without making changes.
    With ``--verbose``, prints per-file detail during template copy.
    After copying templates, validates each one and prints any issues.
    When Espanso is detected, also performs an initial sync so bundled
    triggers become available without a separate manual sync step.
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
            print("[dry-run] Would generate commands popup")
            print("[dry-run] Would sync templates to Espanso")
        else:
            from espansr.integrations.espanso import sync_to_espanso

            clean_stale_espanso_files()
            generate_launcher_file()
            generate_commands_popup_file()
            print(f"Espanso config: {espanso_dir}")
            print("Launcher: generated")
            print("Commands popup: generated")
            if not sync_to_espanso():
                print("Sync: failed — run 'espansr sync' after resolving the issues above")
    else:
        plat = get_platform()
        if plat == "wsl2":
            print(
                "Espanso config: not found — install Espanso on Windows "
                "(https://espanso.org), then run 'espanso start' from PowerShell"
            )
            _print_wsl_espanso_remediation()
        else:
            print(
                "Espanso config: not found — install Espanso "
                "(https://espanso.org), then run 'espanso start' to initialize"
            )
        print("Launcher: skipped (no Espanso config)")
        print("Commands popup: skipped (no Espanso config)")

    # ── orchestratr manifest ──────────────────────────────────────────────
    from espansr.integrations.orchestratr import (
        generate_manifest,
        manifest_needs_update,
        resolve_orchestratr_apps_dir,
    )

    apps_dir = resolve_orchestratr_apps_dir()

    if dry_run:
        if apps_dir is not None:
            manifest_path = apps_dir / "espansr.yml"
            print(f"[dry-run] Would write orchestratr manifest to {manifest_path}")
        else:
            print("[dry-run] orchestratr not found — would skip app registration")
    elif apps_dir is not None:
        if manifest_needs_update(apps_dir):
            manifest_path = generate_manifest(apps_dir)
            print(f"Registered with orchestratr at {manifest_path}")
        else:
            print("orchestratr manifest: up to date")

        # Clean up old manifest in espansr config dir (legacy location)
        config_dir_path = get_config_dir()
        old_manifest = config_dir_path / "orchestratr.yml"
        if old_manifest.exists():
            old_manifest.unlink()
            print(f"  Cleaned up old manifest at {old_manifest}")
    else:
        print("orchestratr not found — skipping app registration")

    if strict and not espanso_found:
        return 1
    return 0


def _print_bundled_report(report, verbose: bool = False) -> None:
    """Print a human-readable bundled-template drift report."""
    status_lines = {
        "up_to_date": "up to date",
        "missing_local": "missing locally",
        "changed_local": "local copy differs from bundled",
        "invalid_local": "local copy is invalid JSON",
    }

    for entry in report.entries:
        if entry.status == "up_to_date" and not verbose:
            continue
        line = status_lines.get(entry.status, entry.status)
        if entry.detail:
            print(f"  {entry.filename}: {line} ({entry.detail})")
        else:
            print(f"  {entry.filename}: {line}")

    if report.local_only:
        print("Local-only templates preserved:")
        for path in report.local_only:
            print(f"  {path.name}")


def cmd_sync_bundled(args) -> int:
    """Check or apply bundled template updates to the live template store."""
    from espansr.core.templates import (
        TemplateManager,
        apply_bundled_template_report,
        build_bundled_template_report,
    )

    apply = getattr(args, "apply", False) if args else False
    dry_run = getattr(args, "dry_run", False) if args else False
    force = getattr(args, "force", False) if args else False
    verbose = getattr(args, "verbose", False) if args else False

    if force and not apply:
        print(fail("--force requires --apply"))
        return 2

    templates_dir = get_templates_dir()
    report = build_bundled_template_report(
        templates_dir=templates_dir,
        bundled_dir=_get_bundled_dir(),
    )

    if report.errors:
        for error in report.errors:
            print(fail(error))
        return 2

    missing = sum(1 for entry in report.entries if entry.status == "missing_local")
    changed = sum(1 for entry in report.entries if entry.status == "changed_local")
    invalid = sum(1 for entry in report.entries if entry.status == "invalid_local")
    up_to_date = sum(1 for entry in report.entries if entry.status == "up_to_date")

    print(
        "Bundled templates: "
        f"{up_to_date} up to date, {missing} missing locally, "
        f"{changed} changed locally, {invalid} invalid locally"
    )
    _print_bundled_report(report, verbose=verbose)

    if not apply:
        if report.has_drift():
            return 1
        print(ok("Bundled templates are already in sync."))
        return 0

    result = apply_bundled_template_report(
        report,
        manager=TemplateManager(templates_dir=templates_dir),
        dry_run=dry_run,
        force_invalid_local=force,
    )

    if result.copied or result.updated or result.forced:
        prefix = "[dry-run] " if dry_run else ""
        print(
            f"{prefix}Bundled sync: "
            f"{result.copied} copied, {result.updated} updated, {result.forced} forced"
        )
    else:
        if dry_run:
            print("[dry-run] Bundled sync: no bundled changes to apply")
        else:
            print("Bundled sync: no bundled changes to apply")

    if result.skipped_invalid:
        if force:
            print(warn("Some invalid local template(s) could not be backed up and were skipped:"))
        else:
            print(warn("Skipped invalid local template(s); use --apply --force to replace them:"))
        for entry in result.skipped_invalid:
            print(f"  {entry.filename}")
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
            _print_wsl_espanso_remediation()
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

    _auto_pull_if_configured()
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

    _auto_pull_if_configured()
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
    _auto_pull_if_configured()
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
        if get_platform() == "wsl2":
            _warn("WSL2 dependency: Espanso must be installed and started on Windows")

    # 5. Espanso binary
    espanso_bin = shutil.which("espanso")
    platform = get_platform()
    if espanso_bin:
        _ok(f"Espanso binary: {espanso_bin}")
    elif platform == "wsl2":
        _ok("Espanso binary: Windows host (WSL2)")
        # Only suggest remediation when Windows-side Espanso config is not detected.
        if not espanso_dir:
            _warn("WSL2 remediation: run 'espanso start' in PowerShell, then 'espansr doctor'")
    else:
        _fail("Espanso binary: not found")

    # 5b. WSL candidate conflict visibility
    if platform == "wsl2":
        existing_candidates = []
        for p in _get_candidate_paths():
            try:
                if p.exists():
                    existing_candidates.append(p)
            except PermissionError:
                _warn(f"Skipping unreadable candidate path: {p}")
            except OSError as exc:
                _warn(f"Skipping candidate path due to OS error ({exc}): {p}")
        if espanso_dir:
            _ok(f"Canonical Espanso path: {espanso_dir}")
        if len(existing_candidates) > 1:
            _warn("Conflict risk: multiple Espanso candidate paths detected")
            for candidate in existing_candidates:
                if candidate != espanso_dir:
                    _warn(f"  Non-canonical candidate: {candidate}")
            _warn("Recommendation: keep one active config path and rerun 'espansr doctor'")

    # 6. Launcher file
    match_dir = get_match_dir()
    if match_dir and (match_dir / "espansr-launcher.yml").exists():
        _ok("Launcher: espansr-launcher.yml present")
    else:
        _fail("Launcher: espansr-launcher.yml not found")

    # 6b. Commands popup file
    if match_dir and (match_dir / "espansr-commands.yml").exists():
        _ok("Commands popup: espansr-commands.yml present")
    else:
        _fail("Commands popup: espansr-commands.yml not found")

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
    _auto_pull_if_configured()
    if getattr(args, "view", "main") == "commands":
        from espansr.ui.commands_popup import launch_commands_popup

        launch_commands_popup()
        return 0

    from espansr.ui.main_window import launch

    launch()
    return 0


def cmd_remote(args) -> int:
    """Manage remote template repository."""
    from espansr.core.remote import GitNotFoundError, RemoteError, RemoteManager

    action = getattr(args, "remote_action", None)
    if not action:
        print("Usage: espansr remote {set,status,remove}")
        return 1

    try:
        rm = RemoteManager()

        if action == "set":
            url = args.url
            rm.set_remote(url)
            print(ok(f"Remote set to {url}"))
            return 0

        if action == "status":
            status = rm.status()
            if not status["url"]:
                print("No remote configured. Run: espansr remote set <git-url>")
                return 0
            print(f"Remote URL:  {status['url']}")
            if status["last_pull"]:
                print(f"Last pull:   {status['last_pull']}")
            if status["last_push"]:
                print(f"Last push:   {status['last_push']}")
            if status["dirty"]:
                print(f"Modified:    {', '.join(status['dirty'])}")
            else:
                print("Modified:    (clean)")
            return 0

        if action == "remove":
            rm.remove_remote()
            print(ok("Remote removed. Local templates preserved."))
            return 0

    except GitNotFoundError as exc:
        print(fail(str(exc)))
        return 1
    except RemoteError as exc:
        print(fail(str(exc)))
        return 1

    return 1


def cmd_pull(args) -> int:
    """Pull templates from remote."""
    from espansr.core.remote import (
        GitNotFoundError,
        RemoteConflictError,
        RemoteError,
        RemoteManager,
    )

    try:
        rm = RemoteManager()
        templates = getattr(args, "template", None)
        if templates:
            rm.pull_templates(templates)
            print(ok(f"Pulled {len(templates)} template(s) from remote."))
        else:
            rm.pull()
            print(ok("Pulled latest templates from remote."))
        return 0
    except RemoteConflictError as exc:
        print(fail(f"Conflict: {exc}"))
        return 1
    except GitNotFoundError as exc:
        print(fail(str(exc)))
        return 1
    except RemoteError as exc:
        print(fail(str(exc)))
        return 1


def cmd_push(args) -> int:
    """Push templates to remote."""
    from espansr.core.remote import GitNotFoundError, RemoteError, RemoteManager

    try:
        rm = RemoteManager()
        message = getattr(args, "message", None)
        templates = getattr(args, "template", None)
        if templates:
            rm.push_templates(templates, message=message)
            print(ok(f"Pushed {len(templates)} template(s) to remote."))
        else:
            rm.push(message=message)
            print(ok("Pushed templates to remote."))
        return 0
    except GitNotFoundError as exc:
        print(fail(str(exc)))
        return 1
    except RemoteError as exc:
        print(fail(str(exc)))
        return 1


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
    bundled_sync_parser = subparsers.add_parser(
        "sync-bundled",
        help="Check or apply bundled template updates to the live store",
    )
    bundled_sync_mode = bundled_sync_parser.add_mutually_exclusive_group()
    bundled_sync_mode.add_argument(
        "--check",
        action="store_true",
        default=False,
        help="Report bundled drift without writing any files (default)",
    )
    bundled_sync_mode.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply bundled template updates to the live template store",
    )
    bundled_sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview what would be updated when used with --apply",
    )
    bundled_sync_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="With --apply, overwrite bundled-matching invalid local JSON after backing it up",
    )
    bundled_sync_parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print per-template bundled drift details",
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
    subparsers.add_parser(
        "wsl-install-espanso",
        help="WSL helper: install/start Espanso on Windows via PowerShell",
    )
    import_parser = subparsers.add_parser(
        "import", help="Import template(s) from a file or directory"
    )
    import_parser.add_argument("path", help="Path to a JSON file or directory of JSON files")
    gui_parser = subparsers.add_parser("gui", help="Launch the GUI")
    gui_parser.add_argument(
        "--view",
        choices=["main", "commands"],
        default="main",
        help="Choose which GUI surface to launch",
    )
    comp_parser = subparsers.add_parser("completions", help="Print shell completion script")
    comp_parser.add_argument(
        "shell",
        choices=["bash", "zsh"],
        help="Target shell (bash or zsh)",
    )

    # ── Remote sync commands ──────────────────────────────────────────────
    remote_parser = subparsers.add_parser("remote", help="Manage remote template repository")
    remote_sub = remote_parser.add_subparsers(dest="remote_action", metavar="ACTION")
    set_parser = remote_sub.add_parser("set", help="Set the remote git URL")
    set_parser.add_argument("url", help="Git remote URL (SSH or HTTPS)")
    remote_sub.add_parser("status", help="Show remote sync status")
    remote_sub.add_parser("remove", help="Disconnect from remote (keeps local templates)")

    pull_parser = subparsers.add_parser("pull", help="Pull templates from remote")
    pull_parser.add_argument(
        "--template",
        action="append",
        metavar="NAME",
        help="Pull only specific template file(s) (repeatable)",
    )

    push_parser = subparsers.add_parser("push", help="Push templates to remote")
    push_parser.add_argument(
        "--template",
        action="append",
        metavar="NAME",
        help="Push only specific template file(s) (repeatable)",
    )
    push_parser.add_argument(
        "--message",
        "-m",
        help="Custom commit message",
    )

    return parser


def main() -> None:
    """Entry point for the espansr CLI."""
    parser = _build_parser()
    args = parser.parse_args()

    handlers = {
        "sync": cmd_sync,
        "sync-bundled": cmd_sync_bundled,
        "status": cmd_status,
        "list": cmd_list,
        "validate": cmd_validate,
        "import": cmd_import,
        "setup": cmd_setup,
        "doctor": cmd_doctor,
        "wsl-install-espanso": cmd_wsl_install_espanso,
        "gui": cmd_gui,
        "completions": cmd_completions,
        "remote": cmd_remote,
        "pull": cmd_pull,
        "push": cmd_push,
    }

    if args.command in handlers:
        sys.exit(handlers[args.command](args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
