"""Tests for the CLI module."""

from __future__ import annotations

from edai import __version__
from edai.cli import _build_config, build_parser
from edai.core.backend_config import BackendConfig


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
            # When no subcommand, args is still a parsed Namespace (not None)
            args = mock_tui.call_args[0][0]
            assert args is not None
            assert args.command is None
            assert args.path is None
            assert args.prompt is None
            assert args.mock is False

    # ── _build_config ──────────────────────────────────────────

    def test_build_config_defaults(self) -> None:
        """_build_config(None) returns default BackendConfig."""
        cfg = _build_config(None)
        assert isinstance(cfg, BackendConfig)
        assert cfg.path is None
        assert cfg.prompt is None
        assert cfg.mock is False

    def test_build_config_path(self) -> None:
        """_build_config passes path through."""
        args = build_parser().parse_args(["--path", "/usr/bin/dc_shell"])
        cfg = _build_config(args)
        assert cfg.path == "/usr/bin/dc_shell"
        assert cfg.mock is False

    def test_build_config_mock(self) -> None:
        """_build_config passes mock flag through."""
        args = build_parser().parse_args(["--mock"])
        cfg = _build_config(args)
        assert cfg.mock is True

    def test_build_config_prompt(self) -> None:
        """_build_config passes prompt through."""
        args = build_parser().parse_args(["--prompt", r"custom>\s*"])
        cfg = _build_config(args)
        assert cfg.prompt == r"custom>\s*"

    def test_build_config_all(self) -> None:
        """_build_config combines all options."""
        args = build_parser().parse_args(
            ["--path", "/bin/tclsh", "--prompt", r"%\s*", "--mock"]
        )
        cfg = _build_config(args)
        assert cfg.path == "/bin/tclsh"
        assert cfg.prompt == r"%\s*"
        assert cfg.mock is True
