"""Tests for the CLI module."""

from __future__ import annotations

from edai import __version__
from edai.cli import build_parser


class TestBuildParser:
    """Verify the argument parser is constructed correctly."""

    def test_version(self) -> None:
        """--version should print the package version and exit."""
        parser = build_parser()
        # argparse raises SystemExit on --version
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            try:
                parser.parse_args(["--version"])
            except SystemExit as e:
                assert e.code == 0
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        assert __version__ in output

    def test_no_command_starts_tui(self) -> None:
        """Running without any subcommand should default to TUI."""
        from unittest.mock import patch

        with patch("edai.cli.cmd_tui", return_value=0) as mock_tui:
            from edai.cli import main

            rc = main([])
            assert rc == 0
            mock_tui.assert_called_once_with(None)
