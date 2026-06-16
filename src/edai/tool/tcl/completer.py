"""Context-aware tab-completer for the EDA Tcl REPL.

Provides prompt_toolkit ``Completer`` implementations that integrate
with ``TclEngine`` for real-time EDA object name completion.

Completion metadata (flags, positional categories, flag value
categories) is read from ``CommandRegistry``, which is populated by
each ``@command(...)`` definition.  This means adding a new command
with the right metadata automatically enables tab completion for it
— no completer changes needed.
"""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

from edai.core.cmd_registry import registry

if TYPE_CHECKING:
    from prompt_toolkit.document import Document

    from edai.tool.tcl.engine import TclEngine


# ── helpers ──────────────────────────────────────────────────────────


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

    Completion metadata is sourced from the global ``CommandRegistry``
    (populated by ``@command(...)`` decorators).
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
        if cmd not in registry:
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
        or a positional argument.  All metadata is sourced from the
        ``CommandRegistry``.
        """
        flags = list(registry.get_command_flags(cmd))
        known_flags = set(flags)

        # Determine context from recent args
        last_arg = args[-1] if args else ""

        # If last arg is a flag, complete its value
        if last_arg in known_flags:
            yield from self._complete_flag_value(cmd, last_arg, word)
            return

        # Track the most recent flag to determine if we're completing its value.
        # Only update when an actual known flag is encountered.
        prev_flag = None
        for a in args:
            if a in known_flags:
                prev_flag = a

        if prev_flag is not None:
            yield from self._complete_flag_value(cmd, prev_flag, word)
            return

        # Check if user is typing a flag name
        if word.startswith("-"):
            for flag in flags:
                if flag.startswith(word):
                    yield Completion(flag, start_position=-len(word))
            return

        # Positional: guess the category based on command metadata
        for cat in registry.get_positional_categories(cmd, completed_pos):
            completions = self._completions_for(cat, word)
            yield from completions

    def _complete_flag_value(  # noqa: PLR0911
        self, cmd: str, flag: str, word: str
    ) -> Iterable[Completion]:
        """Return values appropriate to a given flag.

        Reads completion categories from ``CommandRegistry`` metadata.
        Falls back to engine query helpers for known virtual categories.
        """
        # Check registry metadata first
        cats = registry.get_flag_value_categories(cmd, flag)
        if cats:
            for cat in cats:
                yield from self._completions_for(cat, word)
            return

        # No metadata — no completions for free-form flag values
        return

    def _completions_for(self, category: str, word: str) -> Iterable[Completion]:
        """Yield ``Completion`` items for a given object category.

        Supports virtual categories (e.g. ``"commands"``) in addition
        to those in ``EdaObjectCompleter.CATEGORY_MAP``.
        """
        # Virtual categories first
        if category == "commands":
            for name in self.engine.get_command_names(word):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display=name,
                    display_meta="command",
                )
            return

        # Physical object categories (cells, pins, nets, properties)
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
