import dataclasses as dc
import enum
import inspect
from pathlib import Path
import re
import sys
from collections.abc import Callable, Sequence
from types import NoneType, UnionType
from typing import Annotated, Any, Literal, get_args, get_origin

from ._exceptions import CliBuildError, ParserError
from ._parser import Parser
from .constructors import BoolConstructor, ChoicesConstructor, OptionalConstructor


class NoConstructorError(CliBuildError):
    """Unable to find a valid constructor for a given annotation."""

    def __init__(self, annotation: Any) -> None:
        self._annotation = annotation
        super().__init__(
            f"Must provide callable annotation to act as constructor; got `{self.annotation}`"
        )

    @property
    def annotation(self) -> Any:
        """The annotation that was found."""
        return self._annotation


class CaseType(enum.Enum):
    KEBAB = enum.auto()
    KEBAB_UPPER = enum.auto()
    SNAKE = enum.auto()
    SNAKE_UPPER = enum.auto()
    CAMEL = enum.auto()
    PASCAL = enum.auto()

    def convert(self, value: str, filler: str = "") -> str:
        """Converts the case of the value to the target case type."""
        # Split on kebab, snake, and camelCase/PascalCase word boundaries
        words = list(re.split(r"[-_]|(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", value))
        prefix = ""
        while words and words[0] == "":
            del words[0]
            prefix += filler
        if len(words) == 0:
            raise ValueError(f"Must have at least one word; got `{value}`")
        if self == CaseType.KEBAB:
            return prefix + "-".join(words).lower()
        elif self == CaseType.KEBAB_UPPER:
            return prefix + "-".join(words).upper()
        elif self == CaseType.SNAKE:
            return prefix + "_".join(words).lower()
        elif self == CaseType.SNAKE_UPPER:
            return prefix + "_".join(words).upper()
        elif self == CaseType.CAMEL:
            return prefix + words[0].lower() + "".join(w.capitalize() for w in words[1:])
        elif self == CaseType.PASCAL:
            return prefix + "".join(w.capitalize() for w in words)
        raise ValueError(f"Unknown case type `{self}`")


@dc.dataclass(kw_only=True)
class CliConfig:
    """
    Metadata for a CLI parameter, attached via `Annotated`. All members are treated as overrides.
    Any parameters set here will supersede default behavior unless specified otherwise.

    Members:
        description:
            Help string shown in built-in help output for this parameter.
        displayName:
            Overrides the primary flag name derived from the Python parameter name. Affects
            both the actual flag used at the CLI and the name shown in help output.
        displayType:
            Overrides the type or value label shown in help output. Also used as the
            metavar, e.g. `--output <FILE>` instead of `--output <Path>`.
        aliases:
            A list of alternative flag names that can be used to set this parameter.
        flags:
            If `None`, inferred from the Python signature: parameters without a default become
            positionals; parameters with a default become flags named after the parameter. If an
            explicit sequence, those exact flags are used and the parameter is unconditionally
            treated as a flag option.
        constructor:
            Overrides the constructor derived from the type annotation.
            For non-array options: called on the collected token string(s) immediately.
            For array options: a finalizer called once on the complete list of accumulated
            raw tokens after all argv has been consumed. With `count=1` the list contains
            plain strings; with `count>1` it contains tuples of strings. Defaults to `str`
            for non-array options (e.g. `BoolConstructor` for `bool` annotations) and
            `list` for array options.
        defaultFactory:
            A zero-argument callable that produces the value to use when this option is
            absent from the command line. Setting this makes the option optional regardless of
            whether the Python parameter has a default, and decouples the CLI fallback from the
            function signature (useful for dynamic defaults such as environment variables).
        count:
            Overrides the number of CLI values consumed per invocation.
            For `repeatable` type options, this parameter dictates the number of args required for
            one element to be added to the array.

            If set to 0, the options is treated as a "flag only" option; no value will be
            consumed from the CLI when the user passes this option, and the constructor will be
            called with the value `"True"`. The constructor is never called if the flag isn't
            passed by the user.

            Must be ≥0.

            Variable-length consumption is not supported. To accept a variable number of
            values in a single invocation, use `count=1` and pass the values as a Python
            literal (e.g. ``+[1, 2, 3]``). The constructor can then call `plus_literal` or
            `literal` internally and validate the resulting shape.
        repeatable:
            Overrides array accumulation behaviour.
            If `True`, this option can be called multiple times. Raw tokens are accumulated
            into a list and passed to the constructor as a single finalizer call after parsing
            completes. If `count` is greater than 1, each invocation contributes a tuple of
            strings to the list rather than a plain string.
        sticky:
            If `True`, the option consumes every subsequent token as a value, including tokens
            that look like other flags, until argv is exhausted or a `stickyStopFlag` is
            encountered.
        stickyStopFlag: If set, this flag can be used by the user to stop a sticky option from
            consuming tokens.
        interrupt:
            If set, this callable will be invoked the constructed value as its argument as
            soon as the flag is matched, interrupting parsing immediately.
    """

    description: str | None = dc.field(default=None)
    displayName: str | None = dc.field(default=None)
    displayType: str | None = dc.field(default=None)
    aliases: Sequence[str] | None = dc.field(default=None)
    flags: Sequence[str] | None = dc.field(default=None)
    constructor: Callable[..., Any] | None = dc.field(default=None)
    defaultFactory: Callable[[], Any] | None = dc.field(default=None)
    count: int | None = dc.field(default=None)
    repeatable: bool | None = dc.field(default=None)
    sticky: bool | None = dc.field(default=None)
    stickyStopFlag: str | None = dc.field(default=None)
    interrupt: Callable[[Any], int] | None = dc.field(default=None)


@dc.dataclass(kw_only=True)
class ParamSpec:
    name: str
    annotation: Any
    default: Any
    config: CliConfig | None = dc.field(default=None)

    @property
    def constructor(self) -> Callable[..., Any]:
        """Returns the constructor function to be used for parsing this parameter's value."""
        if self.config and self.config.constructor is not None:
            return self.config.constructor
        if self.config and self.config.repeatable:
            return list
        if self.annotation == inspect._empty:
            return str
        if isinstance(self.annotation, type) and issubclass(self.annotation, enum.Enum):
            return ChoicesConstructor.from_enum(self.annotation)
        if get_origin(self.annotation) is Literal:
            return ChoicesConstructor(*get_args(self.annotation))
        if get_origin(self.annotation) is UnionType:
            args = get_args(self.annotation)
            if (
                len(args) == 2
                and args[0] is not NoneType
                and args[1] is NoneType
                and callable(args[0])
            ):
                return OptionalConstructor(self._constructor_for(args[0]))
        if callable(self.annotation):
            return self._constructor_for(self.annotation)
        raise TypeError(f"Parameter `{self.name}`: `{self.annotation}` is not callable")

    @staticmethod
    def _constructor_for(annotation: Any) -> Callable[..., Any]:
        """Maps a callable annotation to the constructor it should drive; `bool` is strict by default."""
        if annotation is bool:
            return BoolConstructor()
        return annotation

    @property
    def isFlag(self) -> bool:
        """`True` if arg count is 0 for this spec."""
        if self.config and self.config.count == 0:
            return True
        return False

    @property
    def isPositional(self) -> bool:
        """True when the spec has no explicit flags and no Python default."""
        if self.config and self.config.flags is not None:
            return False
        return self.default is inspect._empty

    @property
    def isRequired(self) -> bool:
        """True when the option must be provided on the command line."""
        if self.config and self.config.defaultFactory:
            return False
        return self.default is inspect._empty

    @property
    def count(self) -> int:
        """Number of CLI values consumed per invocation."""
        if self.config and self.config.count is not None:
            return self.config.count
        return 1

    @property
    def isRepeatable(self) -> bool:
        """True when this option accumulates into a list."""
        return bool(self.config and self.config.repeatable)

    @property
    def isSticky(self) -> bool:
        """True when this option continues consuming values until the next flag."""
        return bool(self.config and self.config.sticky)

    @property
    def stickyStopFlag(self) -> str | None:
        return self.config.stickyStopFlag if self.config else None

    @property
    def displayName(self) -> str:
        """Display name for this spec; reverts to regular name if unavailable."""
        if self.config and self.config.displayName is not None:
            return self.config.displayName
        return self.name

    @property
    def displayType(self) -> str:
        """Display type for this spec; returns an empty string if unavailable."""
        if self.config and self.config.displayType is not None:
            return self.config.displayType
        if self.annotation != inspect._empty:
            return self._normalize_annotation(self.annotation, suppressNone=True)
        if self.constructor != str and self.constructor.__name__ != "<lambda>":
            return self.constructor.__name__
        return ""

    @property
    def descriptionLines(self) -> list[str]:
        """Individual description lines for this spec."""
        if self.config and self.config.description:
            return self.config.description.splitlines()
        return []

    @classmethod
    def _normalize_annotation(cls, annotation: Any, *, suppressNone: bool = False) -> Any:
        origin = get_origin(annotation)
        if origin is None:
            return getattr(annotation, "__name__", repr(annotation))
        args = get_args(annotation)
        if suppressNone and len(args) == 2 and NoneType in args and args[0] != args[1]:
            return cls._normalize_annotation(
                args[int(args[0] is NoneType)], suppressNone=suppressNone
            )
        name = str(origin).removeprefix("<class '").removesuffix("'>").rsplit(".", 1)[-1]
        if args and name != "Literal":
            if name == "UnionType":
                joint = " | "
                affixes = ("", "")
            else:
                joint = ", "
                affixes = ("[", "]")
            return (
                f"{name}"
                f"{affixes[0]}"
                f"{joint.join(cls._normalize_annotation(arg, suppressNone=suppressNone) for arg in args)}"
                f"{affixes[1]}"
            )
        return name

    def construct_default(self) -> Any | inspect._empty:
        """Builds the default for this spec, if available."""
        if self.config and self.config.defaultFactory:
            return self.config.defaultFactory()
        return self.default

    def flags(
        self, prefix: str, aliasPrefix: str, case: CaseType, *, useDisplayName: bool = True
    ) -> list[str]:
        """
        Builds list of flags that should refer to this spec; the flag is built dynamically from the
        spec if none were provided, prioritizing `displayName` over `name`.
        """
        if self.isPositional:
            return []
        if self.config and self.config.flags is not None:
            flags = list(self.config.flags)
        elif useDisplayName:
            flags = [self.displayName]
        else:
            flags = []
        if self.config and self.config.aliases is not None:
            flags.extend(self.config.aliases)
        output = [
            f"{aliasPrefix if len(flag) == 1 else prefix}{case.convert(flag, filler=aliasPrefix)}"
            for flag in sorted(flags, key=len)
        ]
        if not self.isPositional and not output:
            raise ValueError(f"{self.name} error: Non-positional parameter would have no flags")
        return output

    def add_to_parser(
        self,
        parser: Parser,
        *,
        flags: list[str] | None,
        exception: type[Exception] | None = None,
    ) -> None:
        """Registers this spec as an option on the given parser."""
        parser.add_option(
            self.name,
            flags=flags,
            required=self.isRequired,
            constructor=self.constructor,
            count=self.count,
            repeatable=self.isRepeatable,
            sticky=self.isSticky,
            stickyStopFlag=self.stickyStopFlag,
            exception=exception,
        )


class _InterruptException(Exception):
    """Used internally to short circuit parsing."""


class Cli:
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
    ) -> None:
        """
        Wraps a function as a CLI, deriving argument configuration from its signature.

        Parameters with no default become positional arguments; parameters with defaults become
        keyword arguments. The function's docstring is used as the CLI description as-is, it is
        not parsed for parameter information.

        Raises TypeError at construction time if any parameter's type annotation is not callable
        and has no registered parser.

        Args:
            fn: The function to wrap.
            description: Provide an explicit description rather than relying on `fn` docstring.
            caseSensitive: If `False`, flag names are matched case-insensitively (e.g. `--Output`
                matches `--output`). Values are always passed to constructors unchanged.
            defaultFlags: If `True`, the name of each parameter is used to build the default flags.
            flagCase: Controls the casing convention applied to flag names derived from Python
                parameter names (e.g. `outputFile` → `--output-file` with `KEBAB`, `--output_file`
                with `SNAKE`).
            flagPrefixes: The prefixes prepended to Python parameter names when deriving flag names
                and long aliases (e.g. `"--"` produces `--output` from `output`) or short aliases
                (e.g. `"-"` produces `-o` from `o`).
            helpFlags: Flag or flags that trigger full help output and exit. Pass a tuple to
                register multiple (e.g. `("help", "h")` to get `--help` and `-h` using default
                prefixes). Pass `None` to disable intentional help summoning; compact help on parse
                errors is unaffected.
            indent: Number of spaces to use for indentation when formatting CLI documentation.
        """
        self._fn = fn
        self._caseSensitive = caseSensitive
        self._defaultFlags = defaultFlags
        self._flagCase = flagCase
        self._flagPrefixes = flagPrefixes
        self._helpFlags = helpFlags
        self._indentLevel = indent
        self._description = (
            description
            if description is not None or not self._fn.__doc__
            else inspect.cleandoc(self._fn.__doc__)
        )
        self._interrupts: dict[type[_InterruptException], Callable[[Any], int]] = {}
        self._callSpecs = self._build_specs()
        self._parseSpecs = list(self._callSpecs)
        if self._helpFlags:
            self._parseSpecs.append(self._build_help_spec())
        self._parser = self._build_parser(self._parseSpecs)

    @property
    def function(self) -> Callable:
        return self._fn

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def descriptionLines(self) -> list[str]:
        if self.description:
            return self.description.splitlines()
        return []

    @property
    def caseSensitive(self) -> bool:
        return self._caseSensitive

    @property
    def defaultFlags(self) -> bool:
        return self._defaultFlags

    @property
    def flagCase(self) -> CaseType:
        return self._flagCase

    @property
    def flagPrefixes(self) -> tuple[str, str]:
        return self._flagPrefixes

    @property
    def helpFlags(self) -> Sequence[str] | None:
        return self._helpFlags

    @property
    def indentLevel(self) -> int:
        return self._indentLevel

    @property
    def _indent(self) -> str:
        return " " * self._indentLevel

    def run(self, argv: Sequence[str]) -> int:
        try:
            args, kwargs = self._parser.parse(list(argv))
        except _InterruptException as e:
            handler = self._interrupts.get(type(e))
            if handler is not None:
                return handler(e.args[0])
            raise
        except (ParserError, ValueError) as e:
            self._print_help()
            header = e.__class__.__name__
            if "error" not in header.lower():
                header = f"Error, {header}"
            msg = e.message if isinstance(e, ParserError) else str(e)
            print(f"\n{header}: {msg}", file=sys.stderr)
            return 2
        return self._call(args, kwargs)

    def _build_specs(self) -> list[ParamSpec]:
        """Walks the wrapped function's signature and returns a `ParamSpec` for each parameter."""
        params = []
        for name, param in inspect.signature(self._fn).parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                raise TypeError(f"Parameter `{name}`: *args and **kwargs are not supported")
            annotation, config = self._unwrap_annotated(param.annotation)
            spec = ParamSpec(name=name, annotation=annotation, default=param.default, config=config)
            try:
                _ = spec.constructor
            except TypeError as e:
                raise NoConstructorError(annotation) from e
            params.append(spec)
        return params

    def _build_help_spec(self) -> ParamSpec:
        return ParamSpec(
            name="__help__",
            annotation=bool,
            default=False,
            config=CliConfig(
                description="Shows this help message.",
                displayName="help",
                flags=self._helpFlags,
                count=0,
                interrupt=self._print_help,
            ),
        )

    @staticmethod
    def _unwrap_annotated(annotation: Any) -> tuple[Any, CliConfig | None]:
        """
        Splits an `Annotated` type into its base type and the first `Param` metadata, if present.

        Returns:
            baseType: The base type of the annotation.
            param: The param metadata, or `None` if none was found.
        """
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            for arg in args[1:]:
                if isinstance(arg, CliConfig):
                    return args[0], arg
        return annotation, None

    def _print_help(self, full: bool = False) -> int:
        print(self._format_help(full=full), file=sys.stderr)
        return 0

    def _build_parser(self, specs: list[ParamSpec]) -> Parser:
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

    def main(self) -> None:
        """Parses `sys.argv` and executes the CLI, then exits with its return value."""
        sys.exit(self.run(sys.argv[1:]))

    def _format_help(self, *, full: bool) -> str:
        lines = self.descriptionLines if full else []

        if positionalSpecs := [s for s in self._parseSpecs if s.isPositional]:
            if lines:
                lines.append("")
            lines.append("Positionals:")
            for spec in positionalSpecs:
                lines.append(
                    f"{self._indent}[{spec.displayName}{self._spec_display_properties(spec)}]"
                )
                lines.extend(
                    f"{self._indent * 2}{line}"
                    for line in self._spec_special_description(spec) + spec.descriptionLines
                )

        if optionSpecs := [s for s in self._parseSpecs if not s.isPositional]:
            if lines:
                lines.append("")
            lines.append(f"Options (case-{'' if self._caseSensitive else 'in'}sensitive):")
            for spec in optionSpecs:
                lines.append(
                    f"{self._indent}"
                    f"{' | '.join(spec.flags(*self._flagPrefixes, self._flagCase, useDisplayName=self._defaultFlags))}"
                    f"{self._spec_display_properties(spec)}"
                )
                lines.extend(
                    f"{self._indent * 2}{line}"
                    for line in self._spec_special_description(spec) + spec.descriptionLines
                )

        return "\n".join(lines)

    def _spec_special_description(self, spec: ParamSpec) -> list[str]:
        """Returns special description lines for parameters with specific types."""
        if isinstance(spec.annotation, type) and issubclass(spec.annotation, enum.Enum):
            return [
                f"Choices: {', '.join(repr(member) for member in spec.annotation._member_names_)}"
            ]
        if get_origin(spec.annotation) is Literal:
            return [f"Choices: {', '.join(repr(arg) for arg in get_args(spec.annotation))}"]
        return []

    def _spec_display_properties(self, spec: ParamSpec) -> str:
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
        if spec.default != inspect._empty:
            properties.append(f"default: {self._spec_special_default(spec.default)}")
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
