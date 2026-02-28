"""Tests for espansr doctor command.

Covers: cmd_doctor() — diagnostic checks, status indicators, exit codes,
reuse of existing functions, and argparse registration.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _run_doctor(capsys, **overrides):
    """Run cmd_doctor with common mocks then return (exit_code, output).

    Default mocks simulate a fully healthy environment.
    Pass keyword overrides to replace individual mock return values.
    """
    from espansr.__main__ import cmd_doctor

    # Create real temp dirs so is_dir() calls work
    _tmp = tempfile.mkdtemp()
    _tmp_path = Path(_tmp)
    _config_dir = _tmp_path / "espansr"
    _config_dir.mkdir()
    _match_dir = _tmp_path / "espanso" / "match"
    _match_dir.mkdir(parents=True)
    # Create a real launcher file for the healthy default
    (_match_dir / "espansr-launcher.yml").write_text("matches: []")

    defaults = {
        "config_dir": _config_dir,
        "templates_dir": _config_dir / "templates",
        "espanso_config_dir": _tmp_path / "espanso",
        "match_dir": _match_dir,
        "espanso_binary": "/usr/bin/espanso",
        "platform": "linux",
        "validate_warnings": [],
        "triggered_templates": ["tmpl"],
        "launcher_exists": True,
    }
    defaults.update(overrides)

    # If launcher_exists is False, remove or never create the launcher file
    if defaults["match_dir"] and not defaults["launcher_exists"]:
        launcher = defaults["match_dir"] / "espansr-launcher.yml"
        if launcher.exists():
            launcher.unlink()

    # Build template stub list
    class _Stub:
        name = "stub"
        trigger = ":stub"

    templates = (
        [_Stub() for _ in defaults["triggered_templates"]]
        if defaults["triggered_templates"]
        else []
    )

    class _ManagerStub:
        def iter_with_triggers(self):
            return iter(templates)

    with (
        patch(
            "espansr.__main__.get_config_dir",
            return_value=defaults["config_dir"],
        ),
        patch(
            "espansr.__main__.get_templates_dir",
            return_value=defaults["templates_dir"],
        ),
        patch(
            "espansr.__main__.get_espanso_config_dir",
            return_value=defaults["espanso_config_dir"],
        ),
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=defaults["match_dir"],
        ),
        patch("shutil.which", return_value=defaults["espanso_binary"]),
        patch(
            "espansr.__main__.get_platform",
            return_value=defaults["platform"],
        ),
        patch(
            "espansr.integrations.validate.validate_all",
            return_value=defaults["validate_warnings"],
        ),
        patch(
            "espansr.core.templates.get_template_manager",
            return_value=_ManagerStub(),
        ),
    ):
        exit_code = cmd_doctor(None)

    output = capsys.readouterr().out
    return exit_code, output


# ─── All healthy ─────────────────────────────────────────────────────────────


def test_doctor_all_healthy(capsys):
    """All checks pass → every line shows [ok], exit 0."""
    exit_code, output = _run_doctor(capsys)
    assert exit_code == 0
    assert "[FAIL]" not in output
    # All 7 checks present with [ok]
    assert output.count("[ok]") >= 7


def test_doctor_all_healthy_exit_zero(capsys):
    """Exit code is 0 when everything is healthy."""
    exit_code, _ = _run_doctor(capsys)
    assert exit_code == 0


# ─── Espanso not found ──────────────────────────────────────────────────────


def test_doctor_espanso_config_missing(capsys):
    """Missing Espanso config → [FAIL] for espanso config check."""
    exit_code, output = _run_doctor(
        capsys,
        espanso_config_dir=None,
        match_dir=None,
        launcher_exists=False,
    )
    assert "[FAIL]" in output
    assert exit_code == 1


def test_doctor_espanso_binary_missing(capsys):
    """Missing Espanso binary → [FAIL] for binary check."""
    exit_code, output = _run_doctor(
        capsys,
        espanso_binary=None,
        platform="linux",
    )
    assert exit_code == 1
    lines = output.strip().splitlines()
    binary_lines = [line for line in lines if "binary" in line.lower()]
    assert any("[FAIL]" in line for line in binary_lines)


def test_doctor_espanso_binary_wsl2_ok(capsys):
    """On WSL2, missing native binary → [ok] (runs on Windows host)."""
    exit_code, output = _run_doctor(
        capsys,
        espanso_binary=None,
        platform="wsl2",
    )
    # Should not FAIL — WSL2 doesn't need native binary
    lines = output.strip().splitlines()
    binary_lines = [line for line in lines if "binary" in line.lower()]
    assert any("[ok]" in line for line in binary_lines)


# ─── No templates ───────────────────────────────────────────────────────────


def test_doctor_no_templates(capsys):
    """No triggered templates → [FAIL], exit 1."""
    exit_code, output = _run_doctor(capsys, triggered_templates=[])
    assert exit_code == 1
    lines = output.strip().splitlines()
    template_lines = [line for line in lines if "template" in line.lower()]
    assert any("[FAIL]" in line for line in template_lines)


# ─── Validation ─────────────────────────────────────────────────────────────


def test_doctor_validation_warnings_only(capsys):
    """Validation produces warnings (no errors) → [warn], exit 0."""
    from espansr.integrations.validate import ValidationWarning

    warnings = [
        ValidationWarning(
            severity="warning",
            message="test warning",
            template_name="t",
        )
    ]
    exit_code, output = _run_doctor(capsys, validate_warnings=warnings)
    assert exit_code == 0
    lines = output.strip().splitlines()
    val_lines = [line for line in lines if "valid" in line.lower()]
    assert any("[warn]" in line for line in val_lines)


def test_doctor_validation_errors(capsys):
    """Validation produces errors → [FAIL], exit 1."""
    from espansr.integrations.validate import ValidationWarning

    errors = [
        ValidationWarning(
            severity="error",
            message="test error",
            template_name="t",
        )
    ]
    exit_code, output = _run_doctor(capsys, validate_warnings=errors)
    assert exit_code == 1
    lines = output.strip().splitlines()
    val_lines = [line for line in lines if "valid" in line.lower()]
    assert any("[FAIL]" in line for line in val_lines)


# ─── Launcher ───────────────────────────────────────────────────────────────


def test_doctor_launcher_missing(capsys):
    """Launcher file missing → [FAIL]."""
    exit_code, output = _run_doctor(capsys, launcher_exists=False)
    assert exit_code == 1
    lines = output.strip().splitlines()
    launcher_lines = [line for line in lines if "launcher" in line.lower()]
    assert any("[FAIL]" in line for line in launcher_lines)


def test_doctor_launcher_no_match_dir(capsys):
    """No match dir (no Espanso) → launcher also fails."""
    exit_code, output = _run_doctor(
        capsys,
        espanso_config_dir=None,
        match_dir=None,
        launcher_exists=False,
    )
    assert exit_code == 1


# ─── Subparser registration ────────────────────────────────────────────────


def test_doctor_subparser_registered():
    """The 'doctor' command is registered in argparse."""
    from espansr.__main__ import main

    with patch("sys.argv", ["espansr", "doctor", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        # --help exits with 0
        assert exc_info.value.code == 0


# ─── Output format ─────────────────────────────────────────────────────────


def test_doctor_output_has_status_indicators(capsys):
    """Each output line has one of [ok], [warn], or [FAIL]."""
    _, output = _run_doctor(capsys)
    for line in output.strip().splitlines():
        assert (
            "[ok]" in line or "[warn]" in line or "[FAIL]" in line
        ), f"Line missing status indicator: {line!r}"
