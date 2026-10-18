from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import Annotated, TypeVar

from ._cli import Cli
from ._config import CliConfig
from .constructors import ChoicesConstructor
from .exceptions import DuplicateCommandError

# Python < 3.12 (would use variadic generics otherwise)
T = TypeVar("T")


class Subcommand(Cli):
    """
    Routes a CLI invocation to one of several sub-CLIs based on the first argument.

    Each sub-CLI keeps its own settings, including its `constructors`; the router itself and its
    built-in help subcommand always use `DEFAULT_CONSTRUCTORS`.
    """

    def __init__(
        self,
        subcommands: Mapping[str | Sequence[str], Cli],
        *,
        description: str | None = None,
        helpCommands: Sequence[str] | None = ("help",),
        caseSensitive: bool = True,
        indent: int = 2,
    ) -> None:
        """
        Args:
            subcommands:
                The CLI that handles each subcommand, by name. Keys may be tuples to declare
                multiple names for the same command; the first element is the canonical name shown
                in help, the rest are aliases (e.g. `("commit", "c"): commit_cli`).
            description:
                Description shown in the top-level help output.
            caseSensitive:
                If `True`, the subcommand name is matched case-sensitively. Applies only to this
                router; nested CLIs use their own `caseSensitive` setting.
            helpCommands:
                Names used for the built-in help subcommand. Pass `None` to disable the built-in
                help subcommand entirely.
            indent:
                How many spaces each level of indentation takes in help output.
        """
        self._subcommandDefinitions = subcommands
        self._subcommands: dict[str, Cli] = {}
        self._aliases: dict[str, str] = {}
        self._register_subcommand_definitions(subcommands)
        if helpCommands:
            self._register_help_subcommand(helpCommands, caseSensitive)
        super().__init__(
            self._build_router(caseSensitive, indent),
            description=description,
            caseSensitive=caseSensitive,
            helpFlags=None,
            indent=indent,
        )

    def _register_subcommand_definitions(
        self, subcommands: Mapping[str | Sequence[str], Cli]
    ) -> None:
        """Registers subcommands and their aliases."""
        for key, cmd in subcommands.items():
            if isinstance(key, str):
                key = (key,)
            self._register_subcommand(key[0], cmd, key[1:])

    def _register_subcommand(self, name: str, subcommand: Cli, aliases: Sequence[str]) -> None:
        """
        Registers a subcommand and its aliases, raising `DuplicateCommandError` if the name or any
        of the aliases are already taken.
        """
        self._validate_and_register(self._subcommands, name, subcommand)
        for alias in aliases:
            self._validate_and_register(self._aliases, alias, name)

    def _validate_and_register(self, target: MutableMapping[str, T], name: str, value: T) -> None:
        """
        Adds the name to the target, which is one of the subcommand or alias tables.

        Raises:
            DuplicateCommandError:
                The name is already taken by an existing subcommand or alias.
        """
        if self._subcommand_exists(name):
            raise DuplicateCommandError(name)
        target[name] = value

    def _subcommand_exists(self, name: str) -> bool:
        """Checks if a name is already taken by an existing subcommand or alias."""
        return name in self._subcommands or name in self._aliases

    def _register_help_subcommand(self, helpCommands: Sequence[str], caseSensitive: bool) -> None:
        """Registers the given subcommands for help."""
        self._register_subcommand(
            helpCommands[0], self._build_help(helpCommands, caseSensitive), helpCommands[1:]
        )

    def _build_help(self, commands: Sequence[str], caseSensitive: bool) -> Cli:
        """Builds a help router CLI with alias support."""

        def _help(
            subcommand: Annotated[
                str | None,
                CliConfig(
                    description="Subcommand to show the help for. Shows this help if omitted.",
                    displayType="",
                    displayDefault="",
                    constructor=ChoicesConstructor(
                        *self._all_choices(), *list(commands), caseSensitive=caseSensitive
                    ),
                    defaultFactory=lambda: None,
                ),
            ],
        ) -> int:
            """Shows the help for this application or its subcommand(s)."""
            if subcommand is None:
                target = self
            else:
                target = self._resolve_subcommand(subcommand)
            print(target._format_help(full=True))
            return 0

        return Cli(_help, caseSensitive=caseSensitive, helpFlags=None)

    def _resolve_subcommand(self, subcommand: str) -> Cli:
        """Resolves a subcommand by command name or alias."""
        try:
            return self._subcommands[subcommand]
        except KeyError:
            return self._subcommands[self._aliases[subcommand]]

    def _all_choices(self) -> list[str]:
        """Lists all subcommands and aliases combined."""
        return list(self._subcommands.keys()) + list(self._aliases.keys())

    def _build_router(self, caseSensitive: bool, indent: int) -> Callable[[str, list[str]], int]:
        """Builds a subcommand router with alias support."""

        def _router(
            subcommand: Annotated[
                str,
                CliConfig(
                    description=self._build_subcommand_description(indent),
                    displayType="",
                    constructor=ChoicesConstructor(
                        *self._all_choices(), caseSensitive=caseSensitive
                    ),
                ),
            ],
            subcommandArgv: Annotated[
                list[str] | None,
                CliConfig(
                    displayName="args...",
                    displayType="",
                    displayDefault="",
                    constructor=list,
                    repeatable=True,
                    sticky=True,
                    defaultFactory=lambda: None,
                ),
            ],
        ) -> int:
            """Runs a subcommand from the list of options below."""
            cmd = self._resolve_subcommand(subcommand)
            return cmd.run(subcommandArgv or [])

        return _router

    def _build_subcommand_description(self, indent: int) -> str:
        """
        Builds the description of the subcommands: each name along with its aliases, with its
        description indented below.
        """
        lines = []
        for name, cmd in self._subcommands.items():
            aliases = tuple(a for a, t in self._aliases.items() if t == name)
            title = " | ".join(sorted((name, *aliases), key=len)) if aliases else name
            lines.append(f"{title}:")
            lines.extend(
                f"{' ' * indent}{line}"
                for line in (cmd.descriptionLines or ["No description available."])
            )
        return "\n".join(lines)
