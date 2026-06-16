"""Command-line interface for edai."""

from __future__ import annotations

import argparse
import sys

from edai import __version__


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
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

    # --- repl subcommand (interactive EDA shell) ---
    repl = sub.add_parser("repl", help="Start interactive EDA Tcl REPL")
    repl.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output (show LLM translation steps)",
    )
    repl.add_argument(
        "--history",
        default=".eda_history",
        help="Path to history file (default: .eda_history)",
    )

    return parser


def cmd_repl(args: argparse.Namespace | None = None) -> int:
    """Handle the ``repl`` subcommand — start interactive EDA REPL."""
    from edai.tool.tcl.repl import run_repl

    verbose = args.verbose if args else False
    history = args.history if args and hasattr(args, "history") else ".eda_history"
    return run_repl(verbose=verbose, history_file=history)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the appropriate handler."""
    parser = build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    if args.command is None:
        # No subcommand → default to interactive REPL
        return cmd_repl(None)

    dispatch = {
        "repl": cmd_repl,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
