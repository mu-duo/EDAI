"""Command-line interface for edai."""

from __future__ import annotations

import argparse
import sys

from edai import __version__
from edai.core.backend_config import BackendConfig


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="edai",
        description="EDAI — AI-powered CLI toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=str,
        default=None,
        help="Path to the EDA tool binary (default: auto-detect tclsh on PATH)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help=(
            "Prompt pattern (regex) expected by the EDA tool "
            "(default: infer from binary name)"
        ),
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use in-memory mock backend instead of a real EDA tool",
    )

    sub = parser.add_subparsers(dest="command", title="subcommands")

    # --- tui subcommand (Textual TUI) ---
    sub.add_parser("tui", help="Start Textual TUI (graphical terminal interface)")

    return parser


def _build_config(args: argparse.Namespace | None) -> BackendConfig:
    """Extract :class:`BackendConfig` from parsed arguments."""
    if args is None:
        return BackendConfig()
    return BackendConfig(
        path=args.path,
        prompt=args.prompt,
        mock=args.mock,
        verbose=args.verbose,
    )


def cmd_tui(args: argparse.Namespace | None = None) -> int:
    """Handle the ``tui`` subcommand — start Textual TUI."""
    from edai.ui.app import run_tui

    config = _build_config(args)
    return run_tui(config)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the appropriate handler."""
    parser = build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    if args.command is None:
        # No subcommand → default to Textual TUI
        return cmd_tui(args)

    dispatch = {
        "tui": cmd_tui,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
