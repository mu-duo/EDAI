"""Command-line interface for edai."""

from __future__ import annotations

import argparse
import sys

from edai import __version__


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

    sub = parser.add_subparsers(dest="command", title="subcommands")

    # --- tui subcommand (Textual TUI) ---
    sub.add_parser("tui", help="Start Textual TUI (graphical terminal interface)")

    return parser


def cmd_tui(_args: argparse.Namespace | None = None) -> int:
    """Handle the ``tui`` subcommand — start Textual TUI."""
    from edai.ui.app import run_tui

    return run_tui()


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the appropriate handler."""
    parser = build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    if args.command is None:
        # No subcommand → default to Textual TUI
        return cmd_tui(None)

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
