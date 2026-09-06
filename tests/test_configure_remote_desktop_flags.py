"""`espansr configure-remote-desktop` flags are mutually exclusive."""

import pytest

import espansr.__main__ as cli


@pytest.mark.parametrize(
    "flags",
    [
        ["--auto", "--revert"],
        ["--auto", "--local"],
        ["--local", "--revert"],
        ["--auto", "--local", "--revert"],
    ],
)
def test_conflicting_flags_exit_2(flags, capsys):
    parser = cli._build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["configure-remote-desktop", *flags])
    assert exc_info.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


@pytest.mark.parametrize("flag", ["--auto", "--revert", "--local"])
def test_single_flags_still_parse(flag):
    parser = cli._build_parser()
    args = parser.parse_args(["configure-remote-desktop", flag])
    assert getattr(args, flag.lstrip("-")) is True


def test_no_flags_means_host_mode():
    parser = cli._build_parser()
    args = parser.parse_args(["configure-remote-desktop"])
    assert (args.auto, args.revert, args.local) == (False, False, False)
