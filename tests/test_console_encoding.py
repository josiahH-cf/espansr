"""Windows console encoding hardening: stdout/stderr never raise on an
unencodable character (errors="replace"), the encoding itself is untouched."""

import io
import json
import os
import platform
import subprocess
import sys
from unittest.mock import patch

import pytest

import espansr.__main__ as cli


def _cp1252_stream():
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")


def test_main_reconfigures_streams_to_replace_errors():
    out = _cp1252_stream()
    err = _cp1252_stream()
    assert out.errors == "strict"
    with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
        with pytest.raises(SystemExit) as exc_info:
            cli.main(["--version"])
    assert exc_info.value.code == 0
    assert out.errors == "replace"
    assert err.errors == "replace"
    assert out.encoding == "cp1252"  # never changed
    out.seek(0)
    assert out.buffer.getvalue().startswith(b"espansr ")


def test_harden_console_streams_survives_streams_without_reconfigure():
    class Bare:
        pass

    with patch.object(sys, "stdout", Bare()), patch.object(sys, "stderr", Bare()):
        cli._harden_console_streams()  # must not raise


def test_harden_console_streams_survives_reconfigure_errors():
    class Refusing:
        def reconfigure(self, **kwargs):
            raise ValueError("cannot reconfigure after reading")

    with patch.object(sys, "stdout", Refusing()), patch.object(sys, "stderr", Refusing()):
        cli._harden_console_streams()  # must not raise


def test_replaced_stream_prints_unencodable_character():
    out = _cp1252_stream()
    with patch.object(sys, "stdout", out), patch.object(sys, "stderr", _cp1252_stream()):
        cli._harden_console_streams()
        print("check ✓ mark")
        sys.stdout.flush()
    assert out.buffer.getvalue() in (b"check ? mark\r\n", b"check ? mark\n")


@pytest.mark.skipif(
    platform.system() == "Darwin", reason="macOS config dir is not redirected by env vars"
)
def test_cli_list_survives_cp1252_console(tmp_path):
    """`python -m espansr list` prints a non-cp1252 template name without raising
    under PYTHONIOENCODING=cp1252 (strict)."""
    config_root = tmp_path / "cfg"
    templates_dir = config_root / "espansr" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "check.json").write_text(
        json.dumps({"name": "Check ✓ mark", "content": "x", "trigger": ":chk"}),
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "PYTHONIOENCODING": "cp1252",
        "PYTHONUTF8": "0",
        "XDG_CONFIG_HOME": str(config_root),
        "APPDATA": str(config_root),
        "NO_COLOR": "1",
    }
    result = subprocess.run(
        [sys.executable, "-m", "espansr", "list"],
        capture_output=True,
        env=env,
        timeout=120,
    )
    stdout = result.stdout.decode("cp1252", errors="replace")
    stderr = result.stderr.decode("cp1252", errors="replace")
    assert result.returncode == 0, stderr
    assert "UnicodeEncodeError" not in stderr
    assert ":chk" in stdout
    assert "Check ? mark" in stdout
