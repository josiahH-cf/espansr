"""Tests for espansr doctor command.

Covers: cmd_doctor() — diagnostic checks, status indicators, exit codes,
reuse of existing functions, and argparse registration.

The command-shim helpers are stubbed suite-wide by ``tests/conftest.py``
(``_no_real_shim_mutation``), so cmd_doctor never touches ~/.local/bin here.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

# ─── Helpers ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def run_doctor(capsys, tmp_path):
    """Return a runner that calls cmd_doctor with common mocks.

    The runner returns ``(exit_code, output)``. Default mocks simulate a fully
    healthy environment on real directories under ``tmp_path``; pass keyword
    overrides to replace individual mock return values.
    """
    from espansr.__main__ import cmd_doctor

    def _run(**overrides):
        # Create real dirs so is_dir() calls work
        config_dir = tmp_path / "espansr"
        config_dir.mkdir(exist_ok=True)
        match_dir = tmp_path / "espanso" / "match"
        match_dir.mkdir(parents=True, exist_ok=True)
        # Create real launcher/popup files for the healthy default
        (match_dir / "espansr-launcher.yml").write_text("matches: []")
        (match_dir / "espansr-commands.yml").write_text("matches: []")

        defaults = {
            "config_dir": config_dir,
            "templates_dir": config_dir / "templates",
            "espanso_config_dir": tmp_path / "espanso",
            "match_dir": match_dir,
            "candidate_paths": [tmp_path / "espanso"],
            "espanso_binary": "/usr/bin/espanso",
            "platform": "linux",
            "validate_warnings": [],
            "triggered_templates": ["tmpl"],
            "launcher_exists": True,
            "commands_popup_exists": True,
        }
        defaults.update(overrides)

        # If launcher_exists is False, remove the launcher file
        if defaults["match_dir"] and not defaults["launcher_exists"]:
            launcher = defaults["match_dir"] / "espansr-launcher.yml"
            if launcher.exists():
                launcher.unlink()
        if defaults["match_dir"] and not defaults["commands_popup_exists"]:
            popup_file = defaults["match_dir"] / "espansr-commands.yml"
            if popup_file.exists():
                popup_file.unlink()

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
                "espansr.__main__._get_candidate_paths",
                return_value=defaults["candidate_paths"],
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

    return _run


def _make_windows_config(tmp_path: Path, name: str) -> Path:
    """Create a canonical-looking Espanso config dir with the managed files."""
    canonical = tmp_path / name
    (canonical / "match").mkdir(parents=True)
    (canonical / "match" / "espansr-launcher.yml").write_text("matches: []")
    (canonical / "match" / "espansr-commands.yml").write_text("matches: []")
    return canonical


# ─── All healthy ─────────────────────────────────────────────────────────────


def test_doctor_all_healthy(run_doctor):
    """All checks pass → every line shows [ok], exit 0."""
    exit_code, output = run_doctor()
    assert exit_code == 0
    assert "[FAIL]" not in output
    # All 7 checks present with [ok]
    assert output.count("[ok]") >= 7


def test_doctor_all_healthy_exit_zero(run_doctor):
    """Exit code is 0 when everything is healthy."""
    exit_code, _ = run_doctor()
    assert exit_code == 0


# ─── Espanso not found ──────────────────────────────────────────────────────


def test_doctor_espanso_config_missing(run_doctor):
    """Missing Espanso config → [FAIL] for espanso config check."""
    exit_code, output = run_doctor(
        espanso_config_dir=None,
        match_dir=None,
        launcher_exists=False,
    )
    assert "[FAIL]" in output
    assert exit_code == 1


def test_doctor_espanso_binary_missing(run_doctor):
    """Missing Espanso binary → [FAIL] for binary check."""
    exit_code, output = run_doctor(
        espanso_binary=None,
        platform="linux",
    )
    assert exit_code == 1
    lines = output.strip().splitlines()
    binary_lines = [line for line in lines if "binary" in line.lower()]
    assert any("[FAIL]" in line for line in binary_lines)


def test_doctor_espanso_binary_wsl2_ok(run_doctor):
    """On WSL2, missing native binary → [ok] (runs on Windows host)."""
    exit_code, output = run_doctor(
        espanso_binary=None,
        platform="wsl2",
    )
    # Should not FAIL — WSL2 doesn't need native binary
    lines = output.strip().splitlines()
    binary_lines = [line for line in lines if "binary" in line.lower()]
    assert any("[ok]" in line for line in binary_lines)


def test_doctor_wsl_missing_espanso_prints_dependency_remediation(run_doctor):
    """WSL doctor output includes explicit dependency and remediation guidance."""
    exit_code, output = run_doctor(
        platform="wsl2",
        espanso_config_dir=None,
        match_dir=None,
        launcher_exists=False,
        espanso_binary=None,
        candidate_paths=[],
    )

    assert exit_code == 1
    assert "WSL2 dependency" in output
    assert "espanso start" in output
    assert "espansr doctor" in output


def test_doctor_wsl_conflict_reports_non_canonical_candidates(run_doctor, tmp_path):
    """WSL doctor reports canonical path and warns on additional candidates."""
    canonical = _make_windows_config(tmp_path, "windows_cfg")
    alt = tmp_path / "linux_cfg"
    alt.mkdir()

    exit_code, output = run_doctor(
        platform="wsl2",
        espanso_config_dir=canonical,
        match_dir=canonical / "match",
        candidate_paths=[canonical, alt],
        espanso_binary=None,
    )

    assert exit_code == 0
    assert "Canonical Espanso path" in output
    assert "Conflict risk" in output
    assert "Non-canonical candidate" in output


def test_doctor_wsl_healthy_does_not_print_remediation_warning(run_doctor, tmp_path):
    """Healthy WSL setup should not emit remediation warning noise."""
    canonical = _make_windows_config(tmp_path, "windows_cfg")

    exit_code, output = run_doctor(
        platform="wsl2",
        espanso_config_dir=canonical,
        match_dir=canonical / "match",
        candidate_paths=[canonical],
        espanso_binary=None,
    )

    assert exit_code == 0
    assert "WSL2 remediation" not in output


# ─── No templates ───────────────────────────────────────────────────────────


def test_doctor_no_templates(run_doctor):
    """No triggered templates → [FAIL], exit 1."""
    exit_code, output = run_doctor(triggered_templates=[])
    assert exit_code == 1
    lines = output.strip().splitlines()
    template_lines = [line for line in lines if "template" in line.lower()]
    assert any("[FAIL]" in line for line in template_lines)


# ─── Validation ─────────────────────────────────────────────────────────────


def test_doctor_validation_warnings_only(run_doctor):
    """Validation produces warnings (no errors) → [warn], exit 0."""
    from espansr.integrations.validate import ValidationWarning

    warnings = [
        ValidationWarning(
            severity="warning",
            message="test warning",
            template_name="t",
        )
    ]
    exit_code, output = run_doctor(validate_warnings=warnings)
    assert exit_code == 0
    lines = output.strip().splitlines()
    val_lines = [line for line in lines if "valid" in line.lower()]
    assert any("[warn]" in line for line in val_lines)


def test_doctor_validation_errors(run_doctor):
    """Validation produces errors → [FAIL], exit 1."""
    from espansr.integrations.validate import ValidationWarning

    errors = [
        ValidationWarning(
            severity="error",
            message="test error",
            template_name="t",
        )
    ]
    exit_code, output = run_doctor(validate_warnings=errors)
    assert exit_code == 1
    lines = output.strip().splitlines()
    val_lines = [line for line in lines if "valid" in line.lower()]
    assert any("[FAIL]" in line for line in val_lines)


# ─── Launcher ───────────────────────────────────────────────────────────────


def test_doctor_launcher_missing(run_doctor):
    """Launcher file missing → [FAIL]."""
    exit_code, output = run_doctor(launcher_exists=False)
    assert exit_code == 1
    lines = output.strip().splitlines()
    launcher_lines = [line for line in lines if "launcher" in line.lower()]
    assert any("[FAIL]" in line for line in launcher_lines)


def test_doctor_launcher_no_match_dir(run_doctor):
    """No match dir (no Espanso) → launcher also fails."""
    exit_code, output = run_doctor(
        espanso_config_dir=None,
        match_dir=None,
        launcher_exists=False,
    )
    assert exit_code == 1


def test_doctor_reports_commands_popup_file_missing(run_doctor):
    """Missing commands popup file is reported as a failing diagnostic."""
    exit_code, output = run_doctor(commands_popup_exists=False)
    assert exit_code == 1
    lines = output.strip().splitlines()
    popup_lines = [line for line in lines if "commands popup" in line.lower()]
    assert any("[FAIL]" in line for line in popup_lines)


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


def test_doctor_output_has_status_indicators(run_doctor):
    """Each output line has one of [ok], [warn], or [FAIL]."""
    _, output = run_doctor()
    for line in output.strip().splitlines():
        assert (
            "[ok]" in line or "[warn]" in line or "[FAIL]" in line
        ), f"Line missing status indicator: {line!r}"


# ─── Command availability ──────────────────────────────────────────────────


def test_doctor_reports_command_availability(run_doctor, tmp_path):
    """Doctor surfaces a 'Command availability' line and warns when bin not on PATH."""
    from espansr.core.platform import ShimResult

    # Override the conftest stub for this test: report not on PATH.
    fake_bin = tmp_path / "fake-shim"
    with (
        patch(
            "espansr.core.platform.ensure_command_shim",
            return_value=ShimResult(
                path=fake_bin / "espansr",
                target=tmp_path / "fake-target",
                status="unchanged",
                message="shim ok",
            ),
        ),
        patch("espansr.core.platform.is_user_bin_on_path", return_value=False),
        patch("espansr.core.platform.get_user_bin_dir", return_value=fake_bin),
    ):
        exit_code, output = run_doctor()

    assert exit_code == 0  # availability is warn-only
    assert "Command availability" in output
    # Both lines should appear: the shim status line and the PATH warning.
    assert "[warn] Command availability" in output
    assert "is not on PATH" in output
