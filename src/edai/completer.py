"""Context-aware tab-completer for the EDA Tcl REPL.

Provides prompt_toolkit ``Completer`` implementations that integrate
with ``TclEngine`` for real-time EDA object name completion.
"""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

if TYPE_CHECKING:
    from prompt_toolkit.document import Document

    from edai.tcl_engine import TclEngine


# ── helpers ──────────────────────────────────────────────────────────

_COMMAND_FLAGS = {
    "get_cells": ["-hier", "-filter"],
    "get_pins": ["-of_objects"],
    "get_nets": ["-of_objects"],
    "set_property": [],
    "report_timing": ["-from", "-to", "-nworst"],
    "place_design": [],
    "route_design": [],
    "help": [],
}


def _tokenize(text: str) -> list[str]:
    """Rough token split that preserves incomplete final word.

    Unlike ``shlex.split`` this won't error on an unclosed quote —
    important for mid-typing completion.
    """
    try:
        tokens = shlex.split(text)
    except ValueError:
        # fallback: simple whitespace split
        tokens = text.split()
    return tokens


def _current_word(document: Document) -> str:
    """Return the word being typed right now."""
    return document.get_word_before_cursor(WORD=True)


def _is_inside_bracket(text_before: str) -> bool:
    """Detect if cursor is inside a Tcl ``[...]`` sub-expression."""
    open_count = text_before.count("[")
    close_count = text_before.count("]")
    return open_count > close_count


def _bracket_context(text_before: str) -> str | None:
    """If inside brackets, return everything between the innermost '[' and cursor."""
    idx = text_before.rfind("[")
    if idx == -1:
        return None
    after = text_before[idx + 1 :]
    # if there's a nested ']' from a completed subcommand, skip
    if "]" in after:
        return None
    return after


# ── completers ───────────────────────────────────────────────────────


class EdaObjectCompleter(Completer):
    """Completes EDA design object names (cells, pins, nets, properties).

    Delegates lookups to ``TclEngine``.
    """

    CATEGORY_MAP = {
        "cells": "get_cell_names",
        "pins": "get_pin_names",
        "nets": "get_net_names",
        "properties": "get_property_names",
    }

    def __init__(self, engine: TclEngine, category: str) -> None:
        self.engine = engine
        method = self.CATEGORY_MAP.get(category)
        if method is None:
            msg = f"unknown category: {category}"
            raise ValueError(msg)
        self._lookup = getattr(engine, method)

    def get_completions(
        self,
        document: Document,
        complete_event: object,  # noqa: ARG002
    ) -> Iterable[Completion]:
        word = _current_word(document)
        for name in self._lookup(word):
            yield Completion(
                name,
                start_position=-len(word),
                display=name,
            )


class EdaCompleter(Completer):
    """Top-level context-aware completer for the EDA Tcl REPL.

    Handles, in order of priority:

    1. ``$var`` → variable name expansion
    2. ``[...]`` → nested Tcl subcommand completion (delegates to self)
    3. Command-specific flag names
    4. Top-level command names
    5. Positional arguments based on the current command (cells, pins, etc.)
    """

    def __init__(self, engine: TclEngine) -> None:
        self.engine = engine

    def get_completions(
        self,
        document: Document,
        complete_event: object,  # noqa: ARG002
    ) -> Iterable[Completion]:
        text_before = document.text_before_cursor
        word = _current_word(document)

        # 1. Variable expansion
        if word.startswith("$"):
            yield from self._complete_var(word)
            return

        # 2. Inside Tcl [...]
        if _is_inside_bracket(text_before):
            inner = _bracket_context(text_before)
            if inner is not None:
                yield from self._complete_inner(inner)
            return

        # 3. Normal command parsing
        yield from self._complete_toplevel(text_before, word)

    # ── internal helpers ─────────────────────────────────────────

    def _complete_var(self, word: str) -> Iterable[Completion]:
        prefix = word[1:]  # strip $
        for name in self.engine.get_variable_names(prefix):
            full = f"${{{name}}}" if "_" in name else f"${name}"
            yield Completion(
                full,
                start_position=-len(word),
                display=f"${name}",
                display_meta=f"({self.engine.variables.get(name, '')})",
            )

    def _complete_inner(self, text: str) -> Iterable[Completion]:
        """Complete inside a ``[...]`` context.

        *text* is everything between the innermost ``[`` and cursor.
        We treat it as a sub-REPL and recursively use top-level completion.
        """
        word = _current_word(Document(text, len(text)))  # noqa: F821  # known symbol
        # get top-level completions for the inner context
        tokens = text.split()
        if not tokens or len(tokens) == 1:
            # completing the command itself
            for name in self.engine.get_command_names(word):
                yield Completion(name, start_position=-len(word))
        else:
            cmd = tokens[0]
            inner_args = tokens[1:]
            inner_completed = max(0, len(inner_args) - 1)
            yield from self._complete_arg(cmd, inner_args, word, inner_completed)

    def _complete_toplevel(self, text_before: str, word: str) -> Iterable[Completion]:
        tokens = _tokenize(text_before)

        # No tokens yet → complete command name
        if not tokens:
            for name in self.engine.get_command_names(""):
                yield Completion(name)
            return

        # Completing the command word (possibly mid-type)
        if len(tokens) == 1 and not text_before.endswith(" "):
            for name in self.engine.get_command_names(word):
                yield Completion(name, start_position=-len(word))
            return

        cmd = tokens[0]

        # Unknown command → no positional completions
        if cmd not in _COMMAND_FLAGS:
            return

        args = tokens[1:]

        # Count *completed* positional args (exclude the partial last token)
        completed_pos = len(args)
        if not text_before.endswith(" ") and len(tokens) > 1:
            completed_pos -= 1  # last token is partial

        # Rebuild full argument list for flag tracking, but pass
        # completed positional count for category lookup
        yield from self._complete_arg(cmd, args, word, completed_pos)

    def _complete_arg(
        self, cmd: str, args: list[str], word: str, completed_pos: int = 0
    ) -> Iterable[Completion]:
        """Complete the current argument position for *cmd*.

        Checks whether we're completing a flag name, a flag value,
        or a positional argument.
        """
        flags = _COMMAND_FLAGS.get(cmd, [])
        known_flags = set(flags)

        # Determine context from recent args
        last_arg = args[-1] if args else ""

        # If last arg is a flag, complete its value
        if last_arg in known_flags:
            yield from self._complete_flag_value(cmd, last_arg, word)
            return

        # If we just finished a flag value, or are on a positional arg
        prev_flag = None
        for a in args:
            prev_flag = a if a in known_flags else None

        if prev_flag is not None:
            yield from self._complete_flag_value(cmd, prev_flag, word)
            return

        # Check if user is typing a flag name
        if word.startswith("-"):
            for flag in flags:
                if flag.startswith(word):
                    yield Completion(flag, start_position=-len(word))
            return

        # Positional: guess the category based on command
        for cat in self._positional_categories(cmd, completed_pos):
            completions = self._completions_for(cat, word)
            yield from completions

    def _positional_categories(self, cmd: str, pos: int) -> list[str]:
        """Return likely completion categories for a positional argument."""
        mapping: dict[str, dict[int, list[str]]] = {
            "get_cells": {0: ["cells"]},
            "get_pins": {0: ["pins"]},
            "get_nets": {0: ["nets"]},
            "set_property": {0: ["properties"], 2: ["cells", "pins"]},
            "report_timing": {},
            "help": {},
        }
        return mapping.get(cmd, {}).get(pos, [])

    def _complete_flag_value(  # noqa: PLR0911
        self, cmd: str, flag: str, word: str
    ) -> Iterable[Completion]:
        """Return values appropriate to a given flag."""
        # -of_objects → cells (or pins for get_pins)
        if flag == "-of_objects":
            if cmd == "get_pins":
                yield from self._completions_for("cells", word)
            else:
                yield from self._completions_for("cells", word)
        elif flag in ("-from", "-to"):
            yield from self._completions_for("pins", word)
        elif flag == "-filter":
            # free-form expression → no completion
            return
        elif flag == "-nworst":
            return  # integer

    def _completions_for(self, category: str, word: str) -> Iterable[Completion]:
        """Yield ``Completion`` items for a given object category."""
        method_name = EdaObjectCompleter.CATEGORY_MAP.get(category)
        if method_name is None:
            return
        lookup = getattr(self.engine, method_name)
        for name in lookup(word):
            yield Completion(
                name,
                start_position=-len(word),
                display=name,
                display_meta=category,
            )
