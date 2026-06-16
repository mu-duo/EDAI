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


class TestHelloCommand:
    """Tests for the ``hello`` subcommand."""

    def test_default(self, cli_runner) -> None:
        """``hello`` without arguments should greet 'World'."""
        rc, out = cli_runner(["hello"])
        assert rc == 0
        assert "Hello, World!" in out

    def test_custom_name(self, cli_runner) -> None:
        """``hello EDAI`` should greet 'EDAI'."""
        rc, out = cli_runner(["hello", "EDAI"])
        assert rc == 0
        assert "Hello, EDAI!" in out

    def test_verbose(self, cli_runner) -> None:
        """``-v hello`` should include the version string."""
        rc, out = cli_runner(["-v", "hello"])
        assert rc == 0
        assert __version__ in out

    def test_no_command_prints_help(self, cli_runner) -> None:
        """Running without any subcommand should return an error."""
        rc, out = cli_runner([])
        assert rc != 0
