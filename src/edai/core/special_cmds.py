"""Special REPL commands (prefixed with ``/``).

Provides a decorator-based registration system for meta-commands that
operate at the REPL level rather than being dispatched to the Tcl engine.
The API mirrors :mod:`edai.core.cmd_registry`.

Usage::

    from edai.core.special_cmds import special_command


    @special_command(name="hello", description="Say hello")
    def cmd_hello(engine, repl, args):
        return "Hello, REPL user!"


Extending::

    # Decorate a plain function with ``@special_command(...)``.
    # The handler receives ``(engine, repl, args)`` and returns
    # ``str | None``.
    #
    # ``aliases=("h", "?")`` adds alternative names.
    # ``hidden=True`` excludes the command from ``/help`` listing.
"""

from __future__ import annotations

from typing import Any, Callable, NamedTuple

from edai.core.Message import Message, MessageRole


class SpecialCommandDef(NamedTuple):
    """Metadata for a registered special command.

    Attributes:
        name: Command name (without ``/``).
        handler: Callable ``(engine, repl, args) -> str | None``.
        description: Human-readable help text.
        aliases: Alternative names for the same command.
        hidden: If True, excluded from ``/help`` listing.

    """

    name: str
    handler: Callable[[Any, Any, list[str]], str | None]
    description: str = ""
    aliases: tuple[str, ...] = ()
    hidden: bool = False


class SpecialCommandRegistry:
    """Registry for ``/``-prefixed REPL commands."""

    def __init__(self) -> None:
        self._commands: dict[str, SpecialCommandDef] = {}
        self._primary_names: set[str] = set()

    # ── registration ─────────────────────────────────────────

    def register(
        self,
        name: str,
        *,
        handler: Callable[[Any, Any, list[str]], str | None],
        description: str = "",
        aliases: tuple[str, ...] = (),
        hidden: bool = False,
    ) -> Callable[[Any, Any, list[str]], str | None]:
        """Register a special command with full metadata.

        Args:
            name: Command name (without ``/``).
            handler: Callable ``(engine, repl, args) -> str | None``.
            description: Human-readable help text.  Falls back to
                ``handler.__doc__``.
            aliases: Alternative names for the same command.
            hidden: If True, excluded from ``/help`` listing.

        Returns:
            The *handler* function (so it can be used as a decorator).

        """
        if not description:
            description = (handler.__doc__ or "").strip()

        cmd = SpecialCommandDef(
            name=name,
            handler=handler,
            description=description,
            aliases=aliases,
            hidden=hidden,
        )
        self._commands[name] = cmd
        self._primary_names.add(name)
        for alias in aliases:
            self._commands[alias] = cmd
        return handler

    def special_command(
        self,
        name: str | None = None,
        *,
        description: str = "",
        aliases: tuple[str, ...] = (),
        hidden: bool = False,
    ) -> Callable:
        """Register a special command via decorator.

        Can be used with or without arguments::

            @special_command
            def my_cmd(engine, repl, args): ...


            @special_command(name="greet", description="Say hello")
            def cmd_greet(engine, repl, args): ...
        """

        def decorator(fn: Callable) -> Callable:
            cmd_name = name or fn.__name__
            self.register(
                name=cmd_name,
                handler=fn,
                description=description,
                aliases=aliases,
                hidden=hidden,
            )
            return fn

        if callable(name):
            # Used as bare @special_command without parentheses
            fn = name
            name = None
            return decorator(fn)

        return decorator

    # ── query ────────────────────────────────────────────────

    def get(self, name: str) -> SpecialCommandDef | None:
        """Look up a special command by name (with or without leading ``/``)."""
        return self._commands.get(name.lstrip("/"))

    def get_names(self, prefix: str = "") -> list[str]:
        """Return primary (non-alias) names matching *prefix*."""
        return sorted(n for n in self._primary_names if n.startswith(prefix))

    def __contains__(self, name: str) -> bool:
        return name.lstrip("/") in self._commands

    def __len__(self) -> int:
        return len(self._primary_names)

    # ── execution ────────────────────────────────────────────

    def execute(self, name: str, engine: Any, repl: Any, args: list[str]) -> str | None:
        """Execute a special command.

        Args:
            name: Command name (with or without leading ``/``).
            engine: ``TclEngine`` instance.
            repl: ``EdaRepl`` instance.
            args: Arguments list.

        Returns:
            Output string, or ``None``.

        Raises:
            CommandError: If the special command is not found.

        """
        cmd = self.get(name)
        if cmd is None:
            from edai.core.cmd_registry import CommandError

            raise CommandError(f"unknown special command: /{name.lstrip('/')}")
        return cmd.handler(engine, repl, args)


# Module-level singleton (all command modules share this)
registry = SpecialCommandRegistry()
special_command = registry.special_command


# ── built-in special commands ─────────────────────────────────


@special_command(
    name="help", aliases=("h", "?"), description="Show available special commands"
)
def _cmd_help(
    engine: Any,  # noqa: ARG001
    repl: Any,  # noqa: ARG001
    args: list[str],  # noqa: ARG001
) -> str | None:
    lines = ["Special commands:", ""]
    for cmd_name in sorted(registry.get_names()):
        cmd = registry.get(cmd_name)
        if cmd is not None and not cmd.hidden:
            alias_list = [a for a in cmd.aliases if a]
            alias_str = f" (aliases: /{', '.join(alias_list)})" if alias_list else ""
            lines.append(f"  /{cmd_name}{alias_str}")
            lines.append(f"      {cmd.description}")
    return "\n".join(lines)


@special_command(
    name="clear", aliases=("cls",), description="Clear the terminal screen"
)
def _cmd_clear(
    engine: Any,  # noqa: ARG001
    repl: Any,  # noqa: ARG001
    args: list[str],  # noqa: ARG001
) -> str | None:
    import sys

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    return None


@special_command(name="exit", aliases=("quit",), description="Exit the REPL")
def _cmd_exit(
    engine: Any,  # noqa: ARG001
    repl: Any,  # noqa: ARG001
    args: list[str],  # noqa: ARG001
) -> str | None:
    raise SystemExit(0)


@special_command(name="debug", description="Toggle verbose/debug mode")
def _cmd_debug(
    engine: Any,  # noqa: ARG001
    repl: Any,
    args: list[str],  # noqa: ARG001
) -> str | None:
    if hasattr(repl, "verbose"):
        repl.verbose = not repl.verbose
        state = "enabled" if repl.verbose else "disabled"
        return f"Debug mode {state}"
    return "Debug mode not available"


@special_command(name="env", description="Show the current environment / engine state")
def _cmd_env(
    engine: Any,
    repl: Any,  # noqa: ARG001
    args: list[str],  # noqa: ARG001
) -> str | None:
    lines = ["Environment:", ""]
    lines.append(f"  Placed:      {getattr(engine, '_placed', '?')}")
    lines.append(f"  Routed:      {getattr(engine, '_routed', '?')}")
    if hasattr(engine, "db"):
        db = engine.db
        lines.append(f"  Cells:       {len(db.get('cells', {}))}")
        lines.append(f"  Nets:        {len(db.get('nets', {}))}")
        lines.append(f"  Ports:       {len(db.get('ports', {}))}")
        lines.append(f"  Clocks:      {len(db.get('clocks', {}))}")
    if hasattr(engine, "variables"):
        lines.append(f"  Variables:   {len(engine.variables)}")
    if hasattr(repl, "verbose"):
        lines.append(f"  Debug mode:  {repl.verbose}")
    return "\n".join(lines)


@special_command(
    name="history",
    aliases=("hist",),
    description="Show conversation history. Usage: /history [N]",
)
def _cmd_history(
    engine: Any,  # noqa: ARG001
    repl: Any,
    args: list[str],
) -> str | None:
    """Show conversation history.

    Usage: /history [N]

    If *N* is provided, shows only the last *N* messages.
    The ``repl`` object must expose ``.conversation`` (or ``._conversation``).
    """
    conversation: list[Message] | None = getattr(repl, "conversation", None)
    if conversation is None:
        conversation = getattr(repl, "_conversation", None)
    if not conversation:
        return "No conversation history available."

    # ── parse optional N argument ──────────────────────────────────
    n: int | None = None
    if args:
        try:
            n = int(args[0])
        except ValueError:
            return f"Invalid argument: {args[0]!r}. Usage: /history [N]"
        if n <= 0:
            return "Number of messages must be positive."

    messages = conversation if n is None else conversation[-n:]

    # ── build output ───────────────────────────────────────────────
    role_styles: dict[MessageRole, str] = {
        MessageRole.HUMAN: "[bold cyan]",
        MessageRole.AI: "[bold green]",
        MessageRole.TOOL: "[bold yellow]",
        MessageRole.SYSTEM: "[dim]",
    }

    # Find the number of leading digits we'll need
    offset = (len(conversation) - len(messages)) + 1 if n is not None else 1
    lines = ["Conversation history:", ""]
    for idx, msg in enumerate(messages, start=offset):
        style = role_styles.get(msg.role, "")
        role_label = msg.role.value.upper()
        # Truncate long content for readability
        content = msg.content[:200] + "…" if len(msg.content) > 200 else msg.content
        lines.append(f"  {idx:>3}. {style}{role_label}:[/] {content}")

    return "\n".join(lines)
