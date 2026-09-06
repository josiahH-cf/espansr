"""Remote URLs with embedded credentials are never printed in plain text."""

from unittest.mock import MagicMock, patch

import pytest

import espansr.__main__ as cli
from espansr.core.remote import RemoteError


@pytest.mark.parametrize(
    "raw, masked",
    [
        (
            "https://alice:s3cret@github.com/alice/templates.git",
            "https://alice:***@github.com/alice/templates.git",
        ),
        ("ssh://git@github.com/alice/templates.git", "ssh://git@github.com/alice/templates.git"),
        ("git@github.com:alice/templates.git", "git@github.com:alice/templates.git"),
        ("https://github.com/alice/templates.git", "https://github.com/alice/templates.git"),
        ("https://token123@github.com/alice/t.git", "https://token123@github.com/alice/t.git"),
        (
            "fatal: unable to access 'https://bob:pw@host/x.git': timeout",
            "fatal: unable to access 'https://bob:***@host/x.git': timeout",
        ),
        ("", ""),
    ],
)
def test_mask_url_credentials(raw, masked):
    assert cli._mask_url_credentials(raw) == masked


def test_mask_handles_none():
    assert cli._mask_url_credentials(None) == ""


def _args(**kw):
    return type("A", (), kw)()


def test_remote_set_prints_masked_url(capsys):
    manager = MagicMock()
    with patch("espansr.core.remote.RemoteManager", return_value=manager):
        rc = cli.cmd_remote(
            _args(remote_action="set", url="https://alice:s3cret@example.com/t.git")
        )
    out = capsys.readouterr().out
    assert rc == 0
    manager.set_remote.assert_called_once_with("https://alice:s3cret@example.com/t.git")
    assert "s3cret" not in out
    assert "https://alice:***@example.com/t.git" in out


def test_remote_status_prints_masked_url(capsys):
    manager = MagicMock()
    manager.status.return_value = {
        "url": "https://alice:s3cret@example.com/t.git",
        "last_pull": "",
        "last_push": "",
        "dirty": [],
    }
    with patch("espansr.core.remote.RemoteManager", return_value=manager):
        rc = cli.cmd_remote(_args(remote_action="status"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "s3cret" not in out
    assert "Remote URL:  https://alice:***@example.com/t.git" in out


def test_pull_error_message_is_masked(capsys):
    manager = MagicMock()
    manager.pull_with_result.side_effect = RemoteError(
        "Failed to fetch from remote: fatal: 'https://alice:s3cret@example.com/t.git'"
    )
    with patch("espansr.core.remote.RemoteManager", return_value=manager):
        rc = cli.cmd_pull(_args(template=None))
    out = capsys.readouterr().out
    assert rc == 1
    assert "s3cret" not in out
    assert "alice:***@example.com" in out


def test_push_error_message_is_masked(capsys):
    manager = MagicMock()
    manager.push.side_effect = RemoteError("Push failed: https://alice:s3cret@example.com/t.git")
    with patch("espansr.core.remote.RemoteManager", return_value=manager):
        rc = cli.cmd_push(_args(template=None, message=None))
    out = capsys.readouterr().out
    assert rc == 1
    assert "s3cret" not in out
