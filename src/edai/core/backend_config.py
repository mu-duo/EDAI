"""Backend configuration dataclass and factory for EDA tool backends."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from edai.core.debug import set_debug

# ── shared backend info map ───────────────────────────────────────
# Used by both create_backend() and the prompt/MORE inference helpers.

BACKEND_INFO: dict[str, dict[str, str]] = {
    "dc_shell": {"prompt": r"dc_shell> ", "type": "dc_shell"},
    "innovus": {"prompt": r"innovus> ", "type": "innovus"},
    "genus": {"prompt": r"genus> ", "type": "genus"},
    "vivado": {"prompt": r"vivado% ", "type": "vivado"},
    "tclsh": {"prompt": r"% ", "type": "tclsh"},
    "RainaSynth": {"prompt": r"RainaSynth>> ", "type": "RainaSynth"},
}

# ── more-prompt inference map ─────────────────────────────────────

_TOOL_MORE: dict[str, str | None] = {
    "tclsh": None,  # no pager
    "RainaSynth": None,  # no pager
    # tools not listed default to r"--More--" (dc_shell, innovus, etc.)
}


def _infer_backend_type(bin_path: str) -> str:
    """Infer the ``backend_type`` identifier from a tool binary path.

    Strips directory and ``.exe`` suffix, then looks up the shared
    :data:`BACKEND_INFO` mapping.  Falls back to ``"tclsh"`` for
    unrecognised binaries (case-sensitive match).
    """
    name = Path(bin_path).stem
    info = BACKEND_INFO.get(name)
    return info["type"] if info else "tclsh"


def _infer_more(bin_path: str) -> str | None:
    """Infer the --More-- pattern from the tool binary name.

    Returns ``None`` for tools known to have no pager, otherwise
    defaults to the ``dc_shell``-style ``--More--`` pattern.
    """
    name = Path(bin_path).stem
    return _TOOL_MORE.get(name, r"--More--")


def _infer_prompt(bin_path: str) -> str:
    """Infer the prompt pattern from the tool binary name.

    Strips directory and ``.exe`` suffix, then looks up the shared
    :data:`BACKEND_INFO` mapping.  Falls back to ``tclsh``-style
    ``%`` prompt for unrecognised binaries.
    """
    name = Path(bin_path).stem
    info = BACKEND_INFO.get(name)
    return info["prompt"] if info else r"% "


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
    verbose: bool = False
    more_pattern: str | None = None


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


def _find_rainasynth() -> str | None:
    """Locate ``RainaSynth`` on ``RAINA_PATH``, or return ``None``."""
    path_dirs = os.environ.get("RAINA_PATH", "").split(os.pathsep)
    for d in path_dirs:
        candidate = os.path.join(d, "RainaSynth")
        if os.path.isfile(candidate):
            return candidate
        candidate_exe = f"{candidate}.exe"
        if os.path.isfile(candidate_exe):
            return candidate_exe

    # detect RainaSynth in ${workspace}
    # detect the path: thor_core/bin/RainaSynth
    workspace = Path().cwd().absolute()
    RainaSynthProject = "thor_core"
    if RainaSynthProject in workspace.parts:
        thor_core_index = workspace.parts.index(RainaSynthProject)
        thor_core_path = Path(*workspace.parts[: thor_core_index + 1])
        candidate = thor_core_path / "bin" / "RainaSynth"
        if candidate.is_file():
            return str(candidate)
        candidate_exe = candidate.with_suffix(".exe")
        if candidate_exe.is_file():
            return str(candidate_exe)

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
    set_debug(cfg.verbose)

    # ── explicit mock ──────────────────────────────────────────
    if cfg.mock:
        if cfg.path:
            print(
                "[warning] --mock overrides --path; using mock backend",
                file=sys.stderr,
            )
        from edai.core.mock_repl import MockTclRepl

        backend: Any = MockTclRepl()
        backend.verbose = cfg.verbose
        if backend.intro:
            print(backend.intro)
        return backend

    # ── explicit binary path ───────────────────────────────────
    if cfg.path:
        if not os.path.isfile(cfg.path):
            raise FileNotFoundError(f"EDA tool binary not found: {cfg.path}")
        prompt = cfg.prompt if cfg.prompt is not None else _infer_prompt(cfg.path)
        more = cfg.more_pattern if cfg.more_pattern is not None else _infer_more(cfg.path)
        backend_type = _infer_backend_type(cfg.path)
        from edai.core.eda_interactive import EDAInteractive

        backend = EDAInteractive(
            bin_path=cfg.path,
            prompt=prompt,
            timeout=300,
            more_pattern=more,
            backend_type=backend_type,
        )
        backend.verbose = cfg.verbose
        print(f"Connected to EDA tool: {cfg.path}")
        return backend

    # ── auto-detect RainaSynth on RAINA_PATH ──────────────────────────────
    raina = _find_rainasynth()
    if raina:
        prompt = cfg.prompt if cfg.prompt is not None else _infer_prompt(raina)
        more = cfg.more_pattern if cfg.more_pattern is not None else _infer_more(raina)
        backend_type = _infer_backend_type(raina)
        from edai.core.eda_interactive import EDAInteractive

        backend = EDAInteractive(
            bin_path=raina,
            prompt=prompt,
            timeout=300,
            more_pattern=more,
            backend_type=backend_type,
        )
        backend.verbose = cfg.verbose
        print(f"Connected to RainaSynth: {raina}")
        return backend

    # ── auto-detect tclsh on PATH ──────────────────────────────
    tclsh = _find_tclsh()
    if tclsh:
        prompt = cfg.prompt if cfg.prompt is not None else _infer_prompt(tclsh)
        more = cfg.more_pattern if cfg.more_pattern is not None else _infer_more(tclsh)
        backend_type = _infer_backend_type(tclsh)
        from edai.core.eda_interactive import EDAInteractive

        backend = EDAInteractive(
            bin_path=tclsh,
            prompt=prompt,
            timeout=300,
            more_pattern=more,
            backend_type=backend_type,
        )
        backend.verbose = cfg.verbose
        print(f"Connected to Tcl shell: {tclsh}")
        return backend

    # ── fallback to mock ───────────────────────────────────────
    from edai.core.mock_repl import MockTclRepl

    backend = MockTclRepl()
    backend.verbose = cfg.verbose
    if backend.intro:
        print(backend.intro)
    return backend
