"""EDA-aware completion engine for Textual widgets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from textual.suggester import Suggester

from edai.core.cmd_registry import registry

if TYPE_CHECKING:
    from edai.tool.tcl.engine import TclEngine

# ── category → engine query helper ─────────────────────────────────

_CATEGORY_MAP: dict[str, str] = {
    "cells": "get_cell_names",
    "pins": "get_pin_names",
    "nets": "get_net_names",
    "properties": "get_property_names",
}


class EdaiSuggester(Suggester):
    """EDAI completion engine — Textual ``Suggester`` + sync getter.

    Provides both:
    * async :meth:`get_suggestion` for Textual's ``Suggester`` protocol
    * sync :meth:`completions` for ``TextArea.update_suggestion`` hook
    """

    def __init__(self, engine: TclEngine) -> None:
        super().__init__(use_cache=True, case_sensitive=False)
        self.engine = engine

    # ── async (Textual Suggester protocol) ─────────────────────────

    async def get_suggestion(self, value: str) -> str | None:
        """Async: return the best single completion."""
        return self.completions(value).first

    # ── sync (TextArea hook) ───────────────────────────────────────

    class Completions:
        """A set of completion candidates with a primary suggestion.

        Attributes:
            prefix: The *word* (token) being completed — used by the
                TextArea to compute the correct ghost-text suffix.
        """

        def __init__(self, candidates: list[str], prefix: str = "") -> None:
            self._candidates = candidates
            self.prefix = prefix

        def __bool__(self) -> bool:
            return bool(self._candidates)

        def __len__(self) -> int:
            return len(self._candidates)

        @property
        def first(self) -> str | None:
            """The primary (best) suggestion, or None."""
            return self._candidates[0] if self._candidates else None

        @property
        def all(self) -> list[str]:
            """All matching candidates."""
            return list(self._candidates)

    def completions(self, value: str) -> Completions:
        """Return all completion candidates for *value*.

        Dispatch order:
        1. ``$var`` → variable name
        2. Command name (first word)
        3. Flag name (``-xxx``)
        4. Flag value
        5. Positional argument (cells, pins, nets, …)
        """
        if not value:
            return self.Completions([])

        # ── 1. Variable expansion ─────────────────────────────────
        if "$" in value:
            last_dollar = value.rfind("$")
            var_prefix = value[last_dollar:]
            return self.Completions(self._complete_var_all(value), prefix=var_prefix)

        parts = value.split()

        # ── 2. Command name ───────────────────────────────────────
        if len(parts) == 1 and not value.endswith(" "):
            return self.Completions(
                self.engine.get_command_names(parts[0]), prefix=parts[0]
            )

        if not parts:
            return self.Completions([])

        cmd_name = parts[0]
        if cmd_name not in registry:
            return self.Completions([])

        args = parts[1:]
        typing_new = value.endswith(" ")
        last_arg = args[-1] if args else ""

        # ── 3. Flag name ──────────────────────────────────────────
        if not typing_new and last_arg.startswith("-") and not self._is_flag_value(cmd_name, args):
            flags = self._match_flags(cmd_name, last_arg)
            return self.Completions(flags, prefix=last_arg)

        # ── 4. Flag value ─────────────────────────────────────────
        prev_flag = self._last_flag_in(cmd_name, args)
        if prev_flag is not None:
            typed = "" if typing_new else last_arg
            return self.Completions(
                self._flag_values(cmd_name, prev_flag, typed), prefix=typed
            )

        # ── 5. Positional argument ────────────────────────────────
        completed_pos = len(args) - (0 if typing_new else 1)
        candidates: list[str] = []
        for cat in registry.get_positional_categories(cmd_name, completed_pos):
            candidates.extend(self._match_category(cat, "" if typing_new else last_arg))
        return self.Completions(candidates, prefix="" if typing_new else last_arg)

    # ── helper : variable ──────────────────────────────────────────

    def _complete_var_all(self, value: str) -> list[str]:
        """Return all matching variable completions."""
        last_dollar = value.rfind("$")
        prefix = value[last_dollar + 1 :]
        if not prefix:
            return []
        names = self.engine.get_variable_names(prefix)
        return [f"${{{n}}}" if "_" in n else f"${n}" for n in names]

    # ── helpers : flags / categories ───────────────────────────────

    @staticmethod
    def _match_flags(cmd: str, typed: str) -> list[str]:
        """Return flags matching *typed* prefix."""
        return [f for f in registry.get_command_flags(cmd) if f.startswith(typed)]

    @staticmethod
    def _is_flag_value(cmd: str, args: list[str]) -> bool:
        """Check whether the last complete arg is a value for a preceding flag."""
        known = set(registry.get_command_flags(cmd))
        return any(a in known for a in reversed(args[:-1]))

    @staticmethod
    def _last_flag_in(cmd: str, args: list[str]) -> str | None:
        """Most recent known flag in *args*."""
        known = set(registry.get_command_flags(cmd))
        for a in reversed(args):
            if a in known:
                return a
        return None

    def _flag_values(self, cmd: str, flag: str, typed: str) -> list[str]:
        """All matching values for a flag's category."""
        result: list[str] = []
        for cat in registry.get_flag_value_categories(cmd, flag):
            result.extend(self._match_category(cat, typed))
        return result

    def _match_category(self, category: str, typed: str) -> list[str]:
        """Return object names matching *typed* for a category."""
        if category == "commands":
            return self.engine.get_command_names(typed)
        method = _CATEGORY_MAP.get(category)
        if method is None:
            return []
        lookup: Callable[[str], list[str]] = cast(Callable[[str], list[str]], getattr(self.engine, method))
        return lookup(typed)
