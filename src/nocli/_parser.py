import dataclasses as dc
from collections.abc import Callable, Iterable, Sequence
from typing import Any, TypeAlias, TypeVar

from .exceptions import (
    ConstructionError,
    DuplicateFlagError,
    FlagAlreadyPassedError,
    MissingOptionError,
    MissingValueError,
    UnexpectedTokenError,
    UnrecognizedTokenError,
)

# What the parser produces for a constructor: a direct string, a tuple of strings for any other
# count (empty for none, in which case a lone constructor is called without any), or a list of
# either for a repeatable option
SingleValue = str
MultipleCountValue = tuple[str, ...]
# Python < 3.12 (would use variadic generics otherwise, and `type RepeatableValue[R] = list[R]`)
R = TypeVar("R")
RepeatableValue: TypeAlias = list[R]
RawValue = (
    SingleValue
    | MultipleCountValue
    | RepeatableValue[SingleValue]
    | RepeatableValue[MultipleCountValue]
)


@dc.dataclass(kw_only=True)
class ParserOption:
    """
    The structure of one option, as `Parser.add_option` takes it.

    Attributes:
        name:
            Canonical name of the parameter, used as the key of its value in the results.
        flags:
            The flags the user can pass; empty for a positional.
        required:
            If `False`, the user may omit the option.
        constructor:
            Applied to the raw value collected for the option.
        count:
            How many CLI values one occurrence of the option consumes.
        repeatable:
            If `False`, the option can be given once.
        sticky:
            If `False`, the option consumes only the values it needs.
        stickyStopFlag:
            The flag that stops a sticky option from consuming tokens, if any.
        exception:
            Raised with the constructed value when the option is encountered, if any.
    """

    name: str
    flags: Sequence[str]
    required: bool
    constructor: Callable[..., Any]
    count: int
    repeatable: bool
    sticky: bool
    stickyStopFlag: str | None
    exception: type[Exception] | None

    def __post_init__(self) -> None:
        """
        Raises:
            ValueError:
                `count` is negative.
        """
        if self.count < 0:
            raise ValueError(f"Expected a count ≥0; got {self.count}")


class Parser:
    """
    Collects command line tokens according to the options it is given, and applies each option's
    constructor to what it collected. It knows nothing about types or functions.
    """

    @staticmethod
    def _construct(option: ParserOption, value: RawValue) -> Any:
        """
        Applies the option's constructor to the raw value, turning any failure into a
        `ConstructionError`.

        Args:
            option:
                The option whose constructor to apply.
            value:
                The raw value collected for the option.

        Returns:
            The constructed value.

        Raises:
            ConstructionError:
                The constructor raised an exception.
        """
        try:
            # A mismatched `option.count` and constructor is a developer error, not a library
            # error
            if option.count == 0 and not option.repeatable:
                return option.constructor()  # There are no values to pass
            return option.constructor(value)
        except Exception as e:
            raise ConstructionError(option.name, option.constructor, value, e) from e

    def __init__(
        self,
        *,
        caseSensitive: bool = True,
        allowDuplicates: bool = False,
    ) -> None:
        """
        Args:
            caseSensitive:
                If `True`, flag names are matched case-sensitively at parse time. Values are
                always passed to constructors unchanged regardless of this setting.
            allowDuplicates:
                If `False`, passing the same non-repeatable flag more than once at parse time
                raises `FlagAlreadyPassedError`. Otherwise, the previous value is silently
                overwritten.
        """
        self._caseSensitive = caseSensitive
        self._allowDuplicates = allowDuplicates
        self._positionals = []
        self._options = []

    @property
    def hasPositionals(self) -> bool:
        """Whether any positionals have been configured."""
        return bool(self._positionals)

    def add_option(
        self,
        name: str,
        *,
        flags: Sequence[str] | None = None,
        required: bool = False,
        constructor: Callable[..., Any] | None = None,
        count: int = 1,
        repeatable: bool = False,
        sticky: bool = False,
        stickyStopFlag: str | None = None,
        exception: type[Exception] | None = None,
    ) -> "Parser":
        """
        Adds an option to the parser.

        Args:
            name:
                Canonical name of the parameter. Will be used in the results mapping.
            flags:
                Option flags the user can pass, like `"--option"` and `"-o"`. If no flags are
                given, the option is treated as positional.
            required:
                If `False`, the user may omit the option. Otherwise, the parser raises an
                exception if the option is not given.
            constructor:
                For non-repeatable options: called on the collected token string(s) immediately.
                For repeatable options: a finalizer called once on the complete list of accumulated
                raw tokens after all argv has been consumed. With `count=1` the list contains plain
                strings; with `count>1` it contains tuples of strings. Defaults to `str` for
                non-repeatable options and `list` for repeatable options.
            count:
                The number of CLI values that are required to construct a value. For `repeatable`
                options, this parameter dictates the number of CLI values required for one element
                to be added to the list.

                If set to 0, the option is treated as a "flag only" option; no value will be
                consumed from the CLI when the user passes this option, and the constructor will be
                called without any arguments. The constructor is never called if the flag isn't
                passed by the user. A `repeatable` option still gets the list of its occurrences,
                each of which is an empty tuple.

                Must be ≥0.

                Variable-length consumption is not supported. To accept a variable number of
                values in a single invocation, use `count=1` and pass the values as a Python
                literal (e.g. `+[1, 2, 3]`), which the constructor then evaluates and validates.
            repeatable:
                If `False`, the option can be given once. If `True`, it can be given multiple
                times: raw tokens are accumulated into a list and passed to the constructor as a
                single finalizer call after parsing completes. If `count` is greater than 1, each
                occurrence contributes a tuple of strings to the list rather than a plain string.
            sticky:
                If `False`, the option consumes only the values it needs. If `True`, it consumes
                every subsequent token as a value, including tokens that look like other flags,
                until argv is exhausted or a `stickyStopFlag` is encountered.

                Warning: because other flags do not stop a sticky option, any options declared
                after it can never be set by the user, unless a `stickyStopFlag` has been set.
            stickyStopFlag:
                If given (a common value would be `--`), this flag can be used by the user to stop
                a sticky option from consuming tokens.
            exception:
                If provided, the parser will raise this exception with the value it got from the
                user when this option is encountered.

        Returns:
            This parser, so that calls can be chained.

        Raises:
            DuplicateFlagError:
                One or more flags are already in use by an existing option.
            ValueError:
                `count` is negative.
        """
        if constructor is None:
            constructor = list if repeatable else str
        self._validate_duplicate_flags(flags)
        option = ParserOption(
            name=name,
            flags=flags or [],
            required=required,
            constructor=constructor,
            count=count,
            repeatable=repeatable,
            sticky=sticky,
            stickyStopFlag=stickyStopFlag,
            exception=exception,
        )
        if option.flags:
            self._options.append(option)
        else:
            self._positionals.append(option)
        return self

    def parse(self, argv: Iterable[str]) -> tuple[list, dict[str, Any]]:
        """
        Parses argv against the configured options and returns the constructed values.

        Positional values are returned in declaration order as a list. Flag values are returned as a
        dict keyed by option name. Repeatable options produce lists; all others produce a single
        value.

        Args:
            argv:
                The tokens to parse, in the order the user passed them.

        Returns:
            args:
                Positional values in declaration order.
            kwargs:
                Maps flag option names to their values.

        Raises:
            FlagAlreadyPassedError:
                A non-repeatable flag was passed more than once and `allowDuplicates=False`.
            UnrecognizedTokenError:
                A token did not match any registered flag or positional slot, and required options
                are still outstanding.
            UnexpectedTokenError:
                A token was encountered after all positionals and required options had already been
                satisfied.
            MissingValueError:
                argv was exhausted while collecting values for a multi-value option.
            ConstructionError:
                An option's constructor was unable to construct a value from what was collected.
            MissingOptionError:
                One or more required options were not provided.
        """
        # Disclaimer: this function is a bit of a mess, grown organically through a design
        # iteration into too many responsibilities. The logic is correct and the names are fine,
        # but the function could use a spa day. Soon
        argv = list(argv)
        # Each arg can be a single value, a sequence, or a nested sequence
        args = []
        kwargs = {}
        posIndex = 0
        sticky: ParserOption | None = None
        stickyKey: str | None = None
        while argv:
            arg = argv.pop(0)
            values: list[str] = []
            key = None
            option = self._find_option_by_flag(arg)

            # Sticky
            if sticky is not None:
                if sticky.stickyStopFlag and arg == sticky.stickyStopFlag:
                    sticky = None
                    stickyKey = None
                    continue
                option = sticky
                key = stickyKey
                values.append(arg)

            # Kwargs
            elif option is not None:
                if option.name in kwargs and not option.repeatable and not self._allowDuplicates:
                    raise FlagAlreadyPassedError(arg, kwargs[option.name])
                sticky = None
                stickyKey = None
                key = option.name

            # Args
            elif posIndex < len(self._positionals):
                option = self._positionals[posIndex]
                posIndex += 1
                values.append(arg)

            # Unknown
            else:
                if self._get_missing(args, kwargs):
                    raise UnrecognizedTokenError(arg)
                else:
                    raise UnexpectedTokenError(arg)

            # Early exit for sticky stop flag
            if option.sticky and option.stickyStopFlag and arg == option.stickyStopFlag:
                sticky = None
                stickyKey = None
                # Insert empty element if arg not yet initialized for this sticky option
                if key is None:
                    if len(args) < posIndex:
                        args.append([])
                elif key not in kwargs:
                    kwargs[key] = []
                continue

            # Multi-value options
            for _ in range(option.count - len(values)):
                try:
                    value = argv.pop(0)
                except Exception as e:
                    raise MissingValueError(option.name, len(values), option.count) from e
                values.append(value)

            # Collect raw value(s); construction is deferred to after the loop
            raw = values[0] if option.count == 1 else tuple(values)

            # Interrupt options: construct immediately and raise
            if option.exception is not None:
                raise option.exception(self._construct(option, raw))

            # Record (accumulation only, no construction here)
            if key is None:
                if option.repeatable:
                    if option.sticky and option == sticky:
                        args[-1].append(raw)
                    else:
                        args.append([raw])
                else:
                    args.append(raw)
            else:
                if option.repeatable:
                    if key in kwargs:
                        kwargs[key].append(raw)
                    else:
                        kwargs[key] = [raw]
                else:
                    kwargs[key] = raw

            # Sticky
            if option.sticky:
                sticky = option
                stickyKey = key

        # Apply all constructors now that accumulation is complete
        for i, arg in enumerate(args):
            option = self._positionals[i]
            args[i] = self._construct(option, args[i])
        for option in self._options:
            if option.name not in kwargs:
                continue
            kwargs[option.name] = self._construct(option, kwargs[option.name])

        # Validate
        if missing := self._get_missing(args, kwargs):
            raise MissingOptionError(missing)

        return args, kwargs

    def _validate_duplicate_flags(self, flags: Iterable[str] | None) -> None:
        """
        Checks if any of the given flags are already in use by existing options.

        Raises:
            DuplicateFlagError:
                One or more flags are already in use by an existing option.
        """
        duplicateFlags = []
        for flag in flags or []:
            if self._find_option_by_flag(flag) is not None:
                duplicateFlags.append(flag)
        if duplicateFlags:
            raise DuplicateFlagError(duplicateFlags)

    def _find_option_by_flag(self, flag: str) -> ParserOption | None:
        """Finds an option by flag."""
        caseFunc = str if self._caseSensitive else str.lower
        for option in self._options:
            for optionFlag in option.flags:
                if caseFunc(flag) == caseFunc(optionFlag):
                    return option
        return None

    def _get_missing(self, args: list, kwargs: dict[str, Any]) -> list[ParserOption]:
        """Returns required options that have not yet been provided."""
        missing = [o for o in self._options if o.required and o.name not in kwargs]
        if len(args) < len(self._positionals):
            missing.extend([o for o in self._positionals[len(args) :] if o.required])
        return missing
