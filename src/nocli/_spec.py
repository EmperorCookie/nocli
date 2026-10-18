import dataclasses as dc
import inspect
from collections.abc import Callable
from functools import partial
from typing import Any

from ._case import CaseType
from ._config import CliConfig
from ._defaults import DEFAULT_CONSTRUCTORS
from ._parser import Parser
from .constructors import CallableConstructor, ConstructorAbc
from .exceptions import (
    CliBuildError,
    ConfigConflictError,
    InvalidNameError,
    NoFlagsError,
    ParamConstructorError,
)


def _single(constructor: ConstructorAbc, raw: Any) -> Any:
    """
    Constructs a value from a lone occurrence, with a constructor that expects a list of them.

    Bound to the constructor with `partial`, which keeps that constructor visible to anything that
    inspects the error of a failed construction.
    """
    return constructor([raw])


@dc.dataclass(kw_only=True)
class CliParamSpec:
    """
    Everything `Cli` knows about one parameter of the wrapped function: its signature, its
    `CliConfig`, and the constructor derived for it.

    The constructor is derived on creation, along with how many CLI values it consumes and whether
    it is repeatable, so that a spec that exists is a valid one.

    Attributes:
        name:
            Name of the parameter in the signature.
        annotation:
            The type annotation of the parameter, without its `CliConfig`.
        default:
            The Python default of the parameter, which is `inspect.Parameter.empty` if it has none.
        config:
            The `CliConfig` attached to the parameter, if any.
        constructors:
            The constructor classes asked, in order, to derive a constructor from the annotation.
    """

    name: str
    annotation: Any
    default: Any
    config: CliConfig | None = dc.field(default=None)
    constructors: tuple[type[ConstructorAbc], ...] = dc.field(
        default_factory=lambda: tuple(DEFAULT_CONSTRUCTORS)
    )

    def __post_init__(self) -> None:
        """
        Raises:
            InvalidNameError:
                `CliConfig.displayName` is empty.
            ParamConstructorError:
                The type annotation is unable to produce a constructor.
            ConfigConflictError:
                `CliConfig.count` is set, or `CliConfig.repeatable` is `True`, while the
                constructor owns it.
        """
        config = self.config
        if config and config.displayName is not None and not config.displayName:
            raise InvalidNameError(self.name, config.displayName)
        resolved = self._resolved
        if config and config.count is not None and not self._wrapsPlainCallable:
            raise ConfigConflictError(self.name, "count", config.count, resolved)
        if self._repeatableRequested and not resolved.repeatable:
            raise ConfigConflictError(self.name, "repeatable", self._repeatableRequested, resolved)

    @property
    def constructor(self) -> Callable[..., Any]:
        """The constructor function to be used for parsing this parameter's value."""
        resolved = self._resolved
        if resolved.repeatable and self._repeatableRequested is False:
            # A repeatable constructor opted out of repeating still needs a list
            return partial(_single, resolved)
        return resolved

    @property
    def isFlag(self) -> bool:
        """Whether the option consumes no CLI values."""
        return self.count == 0

    @property
    def isPositional(self) -> bool:
        """Whether the spec has no explicit flags and no Python default."""
        if self.config and self.config.flags is not None:
            return False
        return self.default is inspect.Parameter.empty

    @property
    def isRequired(self) -> bool:
        """Whether the option must be provided on the command line."""
        if self.config and self.config.defaultFactory:
            return False
        return self.default is inspect.Parameter.empty

    @property
    def count(self) -> int:
        """Number of CLI values consumed per invocation."""
        return self._resolved.count

    @property
    def isRepeatable(self) -> bool:
        """Whether the option accumulates into a list."""
        return self._resolved.repeatable and self._repeatableRequested is not False

    @property
    def isSticky(self) -> bool:
        """Whether the option continues consuming values until the next flag."""
        return bool(self.config and self.config.sticky)

    @property
    def stickyStopFlag(self) -> str | None:
        """The flag that stops a sticky option from consuming tokens, if any."""
        return self.config.stickyStopFlag if self.config else None

    @property
    def displayName(self) -> str:
        """The name shown for the spec, which is its `name` unless `CliConfig` overrides it."""
        if self.config and self.config.displayName is not None:
            return self.config.displayName
        return self.name

    @property
    def displayType(self) -> str:
        """
        The type shown for the spec, which is how its constructor describes itself unless
        `CliConfig` overrides it.

        An empty string omits the type from the help output.
        """
        if self.config and self.config.displayType is not None:
            return self.config.displayType
        return str(self._resolved)

    @property
    def descriptionLines(self) -> list[str]:
        """The individual lines of the description of the spec."""
        if self.config and self.config.description:
            return self.config.description.splitlines()
        return []

    @property
    def _resolved(self) -> ConstructorAbc:
        """
        The constructor for this parameter, before the config adjusts how it is used.

        A plain callable from `CliConfig` has no shape of its own, so it takes the `count` and
        `repeatable` of the config.

        Raises:
            ParamConstructorError:
                The type annotation is unable to produce a constructor.
        """
        if self.config and self.config.constructor is not None:
            if isinstance(self.config.constructor, ConstructorAbc):
                return self.config.constructor
            return CallableConstructor(
                self.config.constructor,
                count=1 if self.config.count is None else self.config.count,
                repeatable=bool(self.config.repeatable),
            )
        annotation = str if self.annotation is inspect.Parameter.empty else self.annotation
        try:
            return ConstructorAbc.from_annotation(annotation, *self.constructors)
        except CliBuildError as e:
            raise ParamConstructorError(self.name, e) from e

    @property
    def _repeatableRequested(self) -> bool | None:
        """Whether `CliConfig` makes the option repeatable; `None` if it does not say."""
        return self.config.repeatable if self.config else None

    @property
    def _wrapsPlainCallable(self) -> bool:
        """Whether `CliConfig` provides a plain callable as constructor, which has no shape."""
        return bool(
            self.config
            and self.config.constructor is not None
            and not isinstance(self.config.constructor, ConstructorAbc)
        )

    def construct_default(self) -> Any:
        """
        Builds the default for this spec, if available.

        Returns:
            The result of `defaultFactory` if set, otherwise the Python default, which is
            `inspect.Parameter.empty` when the parameter has none.
        """
        if self.config and self.config.defaultFactory:
            return self.config.defaultFactory()
        return self.default

    def flags(
        self, prefix: str, aliasPrefix: str, case: CaseType, *, useDisplayName: bool = True
    ) -> list[str]:
        """
        Builds the flags that refer to this spec, from its `CliConfig` or else from its name.

        Args:
            prefix:
                Prepended to long flags.
            aliasPrefix:
                Prepended to single character flags, and used to stand in for leading separators.
            case:
                The casing to convert flag names to.
            useDisplayName:
                If `True`, a flag is derived from `displayName` unless explicit `flags` are set.
                Explicit `flags` and `aliases` are always used.

        Returns:
            The flags, shortest first; empty for a positional.

        Raises:
            InvalidNameError:
                A flag has no words to build a name from.
            NoFlagsError:
                There are no flags at all.
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
        output = []
        for flag in sorted(flags, key=len):
            try:
                converted = case.convert(flag, filler=aliasPrefix)
            except ValueError as e:  # The flag has no words to convert
                raise InvalidNameError(self.name, flag) from e
            output.append(f"{aliasPrefix if len(flag) == 1 else prefix}{converted}")
        if not output:
            raise NoFlagsError(self.name)
        return output

    def add_to_parser(
        self,
        parser: Parser,
        *,
        flags: list[str] | None,
        exception: type[Exception] | None = None,
    ) -> None:
        """
        Registers this spec as an option on the given parser.

        Args:
            parser:
                The parser to register the option with.
            flags:
                The flags the user can pass; `None` or empty registers a positional.
            exception:
                If provided, the parser raises it when the option is encountered.
        """
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
