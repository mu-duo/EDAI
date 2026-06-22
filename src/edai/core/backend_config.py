"""Backend configuration dataclass and factory for EDA tool backends."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path


# ── prompt inference map ──────────────────────────────────────────

_TOOL_PROMPTS: dict[str, str] = {
    "dc_shell": r"dc_shell>\s*",
    "innovus": r"innovus>\s*",
    "genus": r"genus>\s*",
    "vivado": r"vivado%\s*",
    "tclsh": r"\%\s*",
    "RainaSynth": r"RainaSynth>>\s*",
}


def _infer_prompt(bin_path: str) -> str:
    """Infer the prompt pattern from the tool binary name.

    Strips directory and ``.exe`` suffix, then looks up the mapping.
    Falls back to ``tclsh``-style ``%`` prompt.
    """
    name = Path(bin_path).stem  # strip directory and .exe
    return _TOOL_PROMPTS.get(name, r"\%\s*")


# ── config dataclass ──────────────────────────────────────────────


@dataclass
class BackendConfig:
    """Configuration for the EDA tool back-end.

    Parameters
    ----------
    path:
        Explicit path to the EDA tool binary.  When *None* the system
        searches for ``tclsh`` on ``PATH``.
    prompt:
        Prompt pattern (regex) expected by the tool.  When *None* the
        prompt is inferred from the binary name via :data:`_TOOL_PROMPTS`.
    mock:
        Force the in-memory mock backend.  When *True* and *path* is
        also set, *path* is ignored and a warning is printed.
    """

    path: str | None = None
    prompt: str | None = None
    mock: bool = False


# ── helpers ───────────────────────────────────────────────────────


def _find_tclsh() -> str | None:
    """Locate ``tclsh`` on ``PATH``, or return ``None``."""
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for d in path_dirs:
        candidate = os.path.join(d, "tclsh")
        if os.path.isfile(candidate):
            return candidate
        candidate_exe = f"{candidate}.exe"
        if os.path.isfile(candidate_exe):
            return candidate_exe
    return None


# ── factory ───────────────────────────────────────────────────────


def create_backend(config: BackendConfig | None = None) -> Any:
    """Create and return a Tcl execution back-end.

    Resolution order
    -----------------
    1.  ``config.mock`` is *True* → return ``MockTclRepl`` (warn if *path*
        was also set).
    2.  ``config.path`` is set → return ``EDAInteractive`` (raise
        ``FileNotFoundError`` if the binary does not exist).
    3.  ``tclsh`` found on ``PATH`` → return ``EDAInteractive``.
    4.  No config and no ``tclsh`` → return ``MockTclRepl`` (fallback).

    The returned object satisfies the :class:`~edai.ui.app.TclBackend`
    protocol.
    """
    cfg = config or BackendConfig()

    # ── explicit mock ──────────────────────────────────────────
    if cfg.mock:
        if cfg.path:
            print(
                "[warning] --mock overrides --path; using mock backend",
                file=sys.stderr,
            )
        from edai.core.mock_repl import MockTclRepl

        backend: Any = MockTclRepl()
        if backend.intro:
            print(backend.intro)
        return backend

    # ── explicit binary path ───────────────────────────────────
    if cfg.path:
        if not os.path.isfile(cfg.path):
            raise FileNotFoundError(f"EDA tool binary not found: {cfg.path}")
        prompt = cfg.prompt if cfg.prompt is not None else _infer_prompt(cfg.path)
        from edai.core.eda_interactive import EDAInteractive

        backend = EDAInteractive(bin_path=cfg.path, prompt=prompt, timeout=300)
        print(f"Connected to EDA tool: {cfg.path}")
        return backend

    # ── auto-detect tclsh on PATH ──────────────────────────────
    tclsh = _find_tclsh()
    if tclsh:
        prompt = cfg.prompt if cfg.prompt is not None else _infer_prompt(tclsh)
        from edai.core.eda_interactive import EDAInteractive

        backend = EDAInteractive(bin_path=tclsh, prompt=prompt, timeout=300)
        print(f"Connected to Tcl shell: {tclsh}")
        return backend

    # ── fallback to mock ───────────────────────────────────────
    from edai.core.mock_repl import MockTclRepl

    backend = MockTclRepl()
    if backend.intro:
        print(backend.intro)
    return backend
