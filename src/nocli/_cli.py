import enum
import inspect
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any, get_args, get_origin

from ._case import CaseType
from ._config import CliConfig
from ._defaults import DEFAULT_CONSTRUCTORS
from ._parser import Parser
from ._spec import CliParamSpec
from .constructors import ConstructorAbc, FlagConstructor
from .exceptions import ParserError, UnsupportedParameterError


class _InterruptException(Exception):
    """Used internally to short circuit parsing."""


class Cli:
    """
    A function wrapped as a command line interface, with arguments derived from its signature.

    Parameters with no default become positional options; parameters with defaults become flag
    options. The function's docstring is used as the CLI description as-is, it is not parsed for
    parameter information.
    """

    @staticmethod
    def _unwrap_annotated(annotation: Any) -> tuple[Any, CliConfig | None]:
        """
        Splits an `Annotated` type into its base type and the first `CliConfig` metadata, if
        present.

        Returns:
            baseType:
                The base type of the annotation.
            config:
                The `CliConfig` metadata, or `None` if none was found.
        """
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            for arg in args[1:]:
                if isinstance(arg, CliConfig):
                    return args[0], arg
        return annotation, None

    def __init__(
        self,
        fn: Callable[..., int],
        *,
        description: str | None = None,
        caseSensitive: bool = True,
        defaultFlags: bool = True,
        flagCase: CaseType = CaseType.KEBAB,
        flagPrefixes: tuple[str, str] = ("--", "-"),
        helpFlags: Sequence[str] | None = ("help", "h"),
        indent: int = 2,
        constructors: Sequence[type[ConstructorAbc]] | None = None,
    ) -> None:
        """
        Args:
            fn:
                The function to wrap.
            description:
                The description shown in help, instead of the docstring of `fn`.
            caseSensitive:
                If `True`, flag names are matched case-sensitively, so `--Output` does not match
                `--output`. Values are always passed to constructors unchanged.
            defaultFlags:
                If `True`, the name of each parameter is used to build the default flags.
            flagCase:
                Controls the casing convention applied to flag names derived from Python parameter
                names (e.g. `outputFile` → `--output-file` with `KEBAB`, `--output_file` with
                `SNAKE`).
            flagPrefixes:
                The prefixes prepended to Python parameter names when deriving flag names and long
                aliases (e.g. `"--"` produces `--output` from `output`) or short aliases (e.g. `"-"`
                produces `-o` from `o`).
            helpFlags:
                Flag or flags that trigger full help output and exit. Pass a tuple to register
                multiple (e.g. `("help", "h")` to get `--help` and `-h` using default prefixes).
                Pass `None` to disable intentional help summoning; compact help on parse errors is
                unaffected.
            indent:
                How many spaces each level of indentation takes in help output.
            constructors:
                The constructor classes used to derive a constructor from each parameter's type
                annotation, in the order they are asked; the first one that handles the annotation
                is used. Replaces `DEFAULT_CONSTRUCTORS` entirely rather than extending it, so
                build your own list (e.g. `[MyConstructor, *DEFAULT_CONSTRUCTORS]`) and pass it
                here. Defaults to `DEFAULT_CONSTRUCTORS`. A `CliConfig` constructor takes
                precedence over this list.

        Raises:
            ParamConstructorError:
                A parameter's type annotation is unable to produce a constructor, e.g. because no
                constructor handles it.
            ConfigConflictError:
                A parameter's `CliConfig` sets `count` or `repeatable` on a constructor that owns
                it.
            ParamNameError:
                A parameter is unable to produce a usable name: see `InvalidNameError` and
                `NoFlagsError`.
            UnsupportedParameterError:
                The function has an `*args` or `**kwargs` parameter.
        """
        self._fn = fn
        self._caseSensitive = caseSensitive
        self._defaultFlags = defaultFlags
        self._flagCase = flagCase
        self._flagPrefixes = flagPrefixes
        self._helpFlags = helpFlags
        self._indentLevel = indent
        self._constructors = tuple(DEFAULT_CONSTRUCTORS if constructors is None else constructors)
        self._description = description
        self._interrupts: dict[type[_InterruptException], Callable[[Any], int]] = {}
        self._callSpecs = self._build_specs()
        self._parser = self._build_parser(self._parseSpecs)

    @property
    def function(self) -> Callable[..., int]:
        """The wrapped function."""
        return self._fn

    @property
    def description(self) -> str | None:
        """The description shown in help, from the argument or the function docstring."""
        if self._description is not None or not self._fn.__doc__:
            return self._description
        return inspect.cleandoc(self._fn.__doc__)

    @property
    def descriptionLines(self) -> list[str]:
        """The individual lines of the description; empty if there is none."""
        if self.description:
            return self.description.splitlines()
        return []

    @property
    def caseSensitive(self) -> bool:
        """Whether flag names are matched case-sensitively."""
        return self._caseSensitive

    @property
    def defaultFlags(self) -> bool:
        """Whether parameter names are used to build the default flags."""
        return self._defaultFlags

    @property
    def flagCase(self) -> CaseType:
        """The casing convention applied to flag names derived from parameter names."""
        return self._flagCase

    @property
    def flagPrefixes(self) -> tuple[str, str]:
        """The prefixes for long and for short flags, in that order."""
        return self._flagPrefixes

    @property
    def helpFlags(self) -> Sequence[str] | None:
        """The flags that trigger full help output; `None` if there are none."""
        return self._helpFlags

    @property
    def indentLevel(self) -> int:
        """Number of spaces used for indentation in help output."""
        return self._indentLevel

    @property
    def constructors(self) -> tuple[type[ConstructorAbc], ...]:
        """The constructor classes used to derive constructors from annotations, in order."""
        return self._constructors

    @property
    def _parseSpecs(self) -> list[CliParamSpec]:
        """The specs of the wrapped function's parameters, followed by the one of the help flag."""
        specs = list(self._callSpecs)
        if self._helpFlags:
            specs.append(self._build_help_spec())
        return specs

    @property
    def _indent(self) -> str:
        """One level of indentation for help output."""
        return " " * self._indentLevel

    def main(self) -> None:
        """Parses `sys.argv` and executes the CLI, then exits with its return value."""
        sys.exit(self.run(sys.argv[1:]))

    def run(self, argv: Sequence[str]) -> int:
        """
        Parses the arguments and calls the wrapped function with the result.

        Parse errors print the compact help and the error to stderr instead of raising.

        Args:
            argv:
                The arguments to parse, without the program name.

        Returns:
            The return value of the wrapped function, or `2` if the arguments could not be parsed.
        """
        try:
            args, kwargs = self._parser.parse(list(argv))
        except _InterruptException as e:
            handler = self._interrupts.get(type(e))
            if handler is not None:
                return handler(e.args[0])
            raise
        except ParserError as e:
            self._print_help()
            header = type(e).__name__
            if "error" not in header.lower():
                header = f"Error, {header}"
            print(f"\n{header}: {e.message}", file=sys.stderr)
            return 2
        return self._call(args, kwargs)

    def _build_specs(self) -> list[CliParamSpec]:
        """
        Walks the wrapped function's signature and returns a `CliParamSpec` for each parameter.
        """
        params = []
        for name, param in inspect.signature(self._fn).parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                raise UnsupportedParameterError(name, param.kind)
            annotation, config = self._unwrap_annotated(param.annotation)
            params.append(
                CliParamSpec(
                    name=name,
                    annotation=annotation,
                    default=param.default,
                    config=config,
                    constructors=self._constructors,
                )
            )
        return params

    def _build_help_spec(self) -> CliParamSpec:
        """Builds the spec for the built-in help flag, which interrupts parsing to print help."""
        return CliParamSpec(
            name="__help__",
            annotation=bool,
            default=False,
            config=CliConfig(
                description="Shows this help message.",
                displayName="help",
                flags=self._helpFlags,
                constructor=FlagConstructor(),
                interrupt=self._print_help,
            ),
            constructors=self._constructors,
        )

    def _build_parser(self, specs: list[CliParamSpec]) -> Parser:
        """Constructs a Parser from a list of resolved parameter specs."""
        parser = Parser(caseSensitive=self._caseSensitive)

        for spec in specs:
            exception = None
            if spec.config and spec.config.interrupt is not None:
                # Slightly clever code: Dynamically creates an exception class that inherits from
                # `_InterruptException` so that the mapped callback can be invoked as soon as the
                # flag is passed
                exceptionClass = type(f"__Interrupt_{spec.name}", (_InterruptException,), {})
                self._interrupts[exceptionClass] = spec.config.interrupt
                exception = exceptionClass
            spec.add_to_parser(
                parser,
                flags=spec.flags(
                    *self._flagPrefixes, self._flagCase, useDisplayName=self._defaultFlags
                ),
                exception=exception,
            )

        return parser

    def _print_help(self, full: bool = False) -> int:
        """Prints the help to stderr and returns the exit code for having done so."""
        print(self._format_help(full=full), file=sys.stderr)
        return 0

    def _format_help(self, *, full: bool) -> str:
        """Builds the help text; the description is only included when `full`."""
        lines = self.descriptionLines if full else []

        if positionalSpecs := [s for s in self._parseSpecs if s.isPositional]:
            if lines:
                lines.append("")
            lines.append("Positionals:")
            for spec in positionalSpecs:
                lines.append(
                    f"{self._indent}[{spec.displayName}{self._spec_display_properties(spec)}]"
                )
                lines.extend(f"{self._indent * 2}{line}" for line in spec.descriptionLines)

        if optionSpecs := [s for s in self._parseSpecs if not s.isPositional]:
            if lines:
                lines.append("")
            lines.append(f"Options (case-{'' if self._caseSensitive else 'in'}sensitive):")
            for spec in optionSpecs:
                flags = spec.flags(
                    *self._flagPrefixes, self._flagCase, useDisplayName=self._defaultFlags
                )
                lines.append(
                    f"{self._indent}{' | '.join(flags)}{self._spec_display_properties(spec)}"
                )
                lines.extend(f"{self._indent * 2}{line}" for line in spec.descriptionLines)

        return "\n".join(lines)

    def _spec_display_properties(self, spec: CliParamSpec) -> str:
        """Returns a string describing special display properties of the parameter."""
        if spec.displayType and not spec.isFlag:
            typeString = f" <{spec.displayType}>"
        else:
            typeString = ""
        properties = []
        if spec.isFlag:
            properties.append("flag")
        if spec.isRepeatable:
            properties.append("repeatable")
        if spec.isSticky:
            properties.append("sticky")
            if spec.stickyStopFlag is not None:
                properties[-1] += f"[stop=`{spec.stickyStopFlag}`]"
        if spec.isRequired:
            properties.append("required")
        displayDefault = spec.config.displayDefault if spec.config else None
        if displayDefault is not None:
            if displayDefault:  # An empty string omits the default
                properties.append(f"default: {displayDefault}")
        elif (default := spec.construct_default()) is not inspect.Parameter.empty:
            properties.append(f"default: {self._spec_special_default(default)}")
        if not properties:
            return typeString
        return f"{typeString} ({', '.join(properties)})"

    def _spec_special_default(self, value: Any) -> str:
        """Returns a string representation of the default value for special types."""
        if isinstance(value, str):
            return repr(value)
        if isinstance(value, Path):
            return repr(str(value))
        if isinstance(value, enum.Enum):
            return repr(value.name)
        return str(value)

    def _call(self, args: list, kwargs: dict) -> int:
        """
        Maps parse results and `defaultFactory` fallbacks to `kwargs`, then calls the wrapped
        function.
        """
        finalKwargs: dict[str, Any] = {}

        for i, spec in enumerate(s for s in self._callSpecs if s.isPositional):
            if i < len(args):
                finalKwargs[spec.name] = args[i]
            elif spec.config and spec.config.defaultFactory is not None:
                finalKwargs[spec.name] = spec.config.defaultFactory()

        for spec in self._callSpecs:
            if spec.isPositional:
                continue
            if spec.name in kwargs:
                finalKwargs[spec.name] = kwargs[spec.name]
            elif spec.config and spec.config.defaultFactory is not None:
                finalKwargs[spec.name] = spec.config.defaultFactory()

        return self._fn(**finalKwargs)
