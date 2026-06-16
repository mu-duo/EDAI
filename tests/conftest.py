"""Shared fixtures for the test suite."""

from __future__ import annotations

from collections.abc import Callable

import pytest


@pytest.fixture
def cli_runner() -> Callable[[list[str]], tuple[int, str]]:
    """Return a helper that invokes ``edai.cli.main`` and captures exit code + stdout.

    Usage::

        def test_something(cli_runner):
            retcode, stdout = cli_runner(["hello", "EDAI"])
            assert retcode == 0
            assert "Hello, EDAI" in stdout
    """

    def _run(args: list[str]) -> tuple[int, str]:
        import io
        import sys

        from edai.cli import main

        old_stdout = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            rc = main(args)
        finally:
            sys.stdout = old_stdout
        return rc, buf.getvalue()

    return _run
