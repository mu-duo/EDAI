"""Command registration infrastructure for the EDA Tcl engine.

Provides a decorator-based registration system that lets any module
contribute commands without modifying core engine code.

Usage::

    from edai.core.cmd_registry import command

    @command(category="COMMON", flags=("-hier", "-filter"),
             positional_categories={0: ("cells",)})
    def my_cmd(engine, args):
        \"\"\"My docstring becomes the help description.\"\"\"
        ...
        return result_string

    # The handler receives:
    #   engine : TclEngine — for accessing DB, variables, etc.
    #   args   : list[str] — split and substituted command arguments

Completion metadata (``flags``, ``positional_categories``,
``flag_value_categories``) is used by the REPL completer so that every
registered command can participate in tab completion without hardcoding
in the completer itself.
"""

from __future__ import annotations

from typing import Any, Callable, NamedTuple


class CommandDef(NamedTuple):
    """Metadata for a registered command.

    Attributes:
        name: Tcl command name.
        category: Group label for help display.
        usage: Short usage string.
        description: Human-readable help text.
        handler: Callable ``(engine, args) -> str``.
        flags: Flag names for tab completion (e.g. ``("-hier", "-filter")``).
        positional_categories: Dict mapping positional arg index to tuple of
            completion categories (e.g. ``{0: ("cells",)}``).
        flag_value_categories: Dict mapping flag name to tuple of completion
            categories for its value (e.g. ``{"-of_objects": ("cells",)}``).

    """

    name: str
    category: str
    usage: str
    description: str
    handler: Callable[[Any, list[str]], str]
    flags: tuple[str, ...] = ()
    positional_categories: dict[int, tuple[str, ...]] = {}
    flag_value_categories: dict[str, tuple[str, ...]] = {}


class CommandError(Exception):
    """Base error for command execution failures."""


class CommandRegistry:
    """Central registry for EDA Tcl commands.

    Thread-safe for reads; registration happens at import time.
    """

    def __init__(self) -> None:
        self._commands: dict[str, CommandDef] = {}
        self._categories: dict[str, list[str]] = {}

    # ── registration ─────────────────────────────────────────

    def register(
        self,
        name: str,
        *,
        category: str,
        handler: Callable[[Any, list[str]], str],
        usage: str | None = None,
        description: str | None = None,
        flags: tuple[str, ...] | None = None,
        positional_categories: dict[int, tuple[str, ...]] | None = None,
        flag_value_categories: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        """Register a command with full metadata.

        Args:
            name: Tcl command name (e.g. ``get_cells``).
            category: Group label (e.g. ``"STA/SDC"``, ``"COMMON"``).
            handler: Callable that receives ``(engine, args)`` and returns output.
            usage: Short usage string for help.
            description: Human-readable description for help.  Falls back to
                ``handler.__doc__``.
            flags: Tuple of flag names for tab completion.
            positional_categories: Dict mapping positional arg index to tuple of
                completion categories.
            flag_value_categories: Dict mapping flag name to tuple of completion
                categories for its value.

        """
        if description is None:
            description = (handler.__doc__ or "").strip()
        if usage is None:
            usage = name

        cmd = CommandDef(
            name=name,
            category=category,
            usage=usage,
            description=description,
            handler=handler,
            flags=flags or (),
            positional_categories=positional_categories or {},
            flag_value_categories=flag_value_categories or {},
        )
        self._commands[name] = cmd
        self._categories.setdefault(category, []).append(name)

    def command(
        self,
        name: str | None = None,
        *,
        category: str = "COMMON",
        usage: str | None = None,
        description: str | None = None,
        flags: tuple[str, ...] | None = None,
        positional_categories: dict[int, tuple[str, ...]] | None = None,
        flag_value_categories: dict[str, tuple[str, ...]] | None = None,
    ) -> Callable:
        """Register a command via decorator.

        Can be used with or without arguments::

            @command(category="STA/SDC")
            def get_pin(engine, args): ...


            @command("get_pin", category="STA/SDC")
            def some_fn(engine, args): ...
        """

        def decorator(fn: Callable) -> Callable:
            cmd_name = name or fn.__name__
            self.register(
                name=cmd_name,
                category=category,
                handler=fn,
                usage=usage,
                description=description,
                flags=flags,
                positional_categories=positional_categories,
                flag_value_categories=flag_value_categories,
            )
            return fn

        if callable(name):
            # Used as bare @command without parentheses
            fn = name
            name = None
            return decorator(fn)

        return decorator

    # ── query ────────────────────────────────────────────────

    def get(self, name: str) -> CommandDef | None:
        """Look up a command by name."""
        return self._commands.get(name)

    def get_handler(self, name: str) -> Callable[[Any, list[str]], str] | None:
        """Return the handler callable for *name*, or ``None``."""
        cmd = self._commands.get(name)
        if cmd is not None:
            return cmd.handler
        return None

    def get_categories(self) -> dict[str, list[str]]:
        """Return ``{category: [command_names]}``."""
        return dict(self._categories)

    def all_commands(self) -> dict[str, CommandDef]:
        """Return a copy of all registered commands."""
        return dict(self._commands)

    def get_command_flags(self, name: str) -> tuple[str, ...]:
        """Return flags for command *name* used by tab completion."""
        cmd = self._commands.get(name)
        if cmd is not None:
            return cmd.flags
        return ()

    def get_positional_categories(self, name: str, pos: int) -> tuple[str, ...]:
        """Return completion categories for positional arg at *pos* of *name*."""
        cmd = self._commands.get(name)
        if cmd is not None:
            return cmd.positional_categories.get(pos, ())
        return ()

    def get_flag_value_categories(self, name: str, flag: str) -> tuple[str, ...]:
        """Return completion categories for a flag's value on command *name*."""
        cmd = self._commands.get(name)
        if cmd is not None:
            return cmd.flag_value_categories.get(flag, ())
        return ()

    def __contains__(self, name: str) -> bool:
        return name in self._commands

    def __len__(self) -> int:
        return len(self._commands)

    # ── execution ───────────────────────────────────────────

    def execute(self, name: str, engine: Any, args: list[str]) -> str:
        """Execute a registered command by name.

        Args:
            name: Command name.
            engine: ``TclEngine`` instance.
            args: List of argument strings.

        Returns:
            Command output string.

        Raises:
            CommandError: If the command is unknown.

        """
        handler = self.get_handler(name)
        if handler is None:
            msg = f"unknown command: {name}"
            raise CommandError(msg)
        return handler(engine, args)


# Module-level singleton (all command modules share this)
registry = CommandRegistry()


# Syntactic sugar: importers can do ``from edai.core.cmd_registry import command``
# where ``command`` is the decorator bound to the global registry.
command = registry.command
