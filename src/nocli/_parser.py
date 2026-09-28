from collections.abc import Callable, Iterable, Sequence
import dataclasses as dc
from typing import Any, TypeVar, TypeAlias

from ._exceptions import ParserError

# Constructors can be called with a direct string, a sequence of strings, or a nested sequence of
# strings
SingleValue = str
MultipleCountValue = tuple[str, ...]
R = TypeVar("R")  # Python < 3.12 (would use variadic generics otherwise)
RepeatableValue: TypeAlias = tuple[
    R, ...
]  # Python < 3.12 (would use `type RepeatableValue[R] = tuple[R, ...]` instead)
RawValue = (
    SingleValue
    | MultipleCountValue
    | RepeatableValue[SingleValue]
    | RepeatableValue[MultipleCountValue]
)

T = TypeVar("T")  # Python < 3.12 (would use variadic generics otherwise)


class DuplicateFlagError(ParserError):
    """One or more flags are already in use by an existing option."""

    def __init__(self, flags: list[str]):
        """
        Args:
            flags: List of flags that are already in use.
        """
        self._flags = flags
        super().__init__(f"Flag must not already exist; got duplicate flags `{self.flags}`")

    @property
    def flags(self) -> list[str]:
        """List of flags that are already in use."""
        return self._flags


class FlagAlreadyPassedError(ParserError):
    """A flag has been passed twice and would overwrite a value."""

    def __init__(self, flag: str, value: Any):
        """
        Args:
            flag: The flag that already has a value.
            value: The value that would be overwritten.
        """
        self._flag = flag
        self._value = value
        super().__init__(
            f"Flag must not be passed more than once"
            f"; got flag `{self.flag}` which would overwrite value `{self.value}`"
        )

    @property
    def flag(self) -> str:
        """The flag that was already passed."""
        return self._flag

    @property
    def value(self) -> Any:
        """The value that would be overwritten."""
        return self._value


class MissingValueError(ParserError):
    """An option was expecting more values than were found."""

    def __init__(self, name: str, found: int, expected: int):
        """
        Args:
            name:
                The name of the option that was expecting more values.
            found:
                Number of values collected before argv was exhausted.
            expected:
                Total number of values the option requires.
        """
        self._name = name
        self._found = found
        self._expected = expected
        super().__init__(f"`{self.name}` expected {self.expected} values; got {self.found}")

    @property
    def name(self) -> str:
        """The name of the option that was expecting more values."""
        return self._name

    @property
    def found(self) -> int:
        """Number of values that were found."""
        return self._found

    @property
    def expected(self) -> int:
        """Number of values that were expected."""
        return self._expected


class UnrecognizedTokenError(ParserError):
    """A token was expected, but the given one is unrecognized."""

    def __init__(self, token: str):
        """
        Args:
            token:
                The token that did not match any registered flag or positional slot.
        """
        self._token = token
        super().__init__(f"Unrecognized token: `{self.token}`")

    @property
    def token(self) -> str:
        """The unrecognized token."""
        return self._token


class UnexpectedTokenError(ParserError):
    """No more tokens were expected, but a token was found anyway."""

    def __init__(self, token: str):
        """
        Args:
            token:
                The extra token encountered after all positionals and required options had already
                been satisfied.
        """
        self._token = token
        super().__init__(f"Unexpected token: `{self.token}`")

    @property
    def token(self) -> str:
        """The unexpected token."""
        return self._token


class MissingOptionError(ParserError):
    """One or more required options is missing."""

    def __init__(self, missing: Iterable["ParserOption"]):
        self._missing = tuple(missing)
        super().__init__(f"One or more options are missing: {', '.join(self.missingFlagsOrNames)}")

    @property
    def missing(self) -> tuple["ParserOption", ...]:
        """The missing options."""
        return self._missing

    @property
    def missingNames(self) -> list[str]:
        """The name of each missing option."""
        return [o.name for o in self.missing]

    @property
    def missingFlagsOrNames(self) -> list[str]:
        """The first flag of each missing option, or the name if there are no flags."""
        return [o.flags[0] if len(o.flags) > 0 else o.name for o in self.missing]


class ConstructionError(ParserError):
    """Failed to parse a user value using the provided constructor."""

    def __init__(self, location: str, constructor: Callable[..., Any], value: RawValue) -> None:
        self._location = location
        self._constructor = constructor
        self._value = value
        super().__init__(f"Failed to parse '{self.location}'; invalid value `{value}`")

    @property
    def location(self) -> str:
        """The location name where the error occurred."""
        return self._location

    @property
    def constructor(self) -> Callable[..., Any]:
        """The constructor that was used and failed."""
        return self._constructor

    @property
    def value(self) -> RawValue:
        """The user value that was passed to the constructor."""
        return self._value


@dc.dataclass
class ParserOption:
    name: str
    flags: Sequence[str]
    required: bool
    constructor: Callable[..., Any]
    count: int
    repeatable: bool
    sticky: bool
    stickyStopFlag: str | None
    exception: type[Exception] | None

    def __post_init__(self):
        if self.count < 0:
            raise ValueError("Count must be ≥0")


class Parser:
    def __init__(
        self,
        *,
        caseSensitive: bool = True,
        allowDuplicates: bool = False,
    ):
        """
        Args:
            caseSensitive: When `False`, flag names are matched case-insensitively at parse time.
                Values are always passed to constructors unchanged regardless of this setting.
            allowDuplicates: When `True`, passing the same non-array flag more than once at parse
                time silently overwrites the previous value.
        """
        self._caseSensitive = caseSensitive
        self._allowDuplicates = allowDuplicates
        self._positionals = []
        self._options = []

    @property
    def hasPositionals(self) -> bool:
        """True if any positionals have been configured for this parser."""
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
            name: Canonical name of the parameter. Will be used in the results mapping.
            flags: Option flags the user can pass, like `"--option"` and `"-o"`. If no flags are
                given, the option is treated as positional.
            required: Causes the parser to raise an exception if that option is not given by the
                user.
            constructor: For non-array options: called on the collected token string(s) immediately.
                For array options: a finalizer called once on the complete list of accumulated
                raw tokens after all argv has been consumed. With `count=1` the list contains
                plain strings; with `count>1` it contains tuples of strings. Defaults to `str`
                for non-array options and `list` for array options.
            count: The number of args that are required to construct a value. For `repeatable` type
                options, this parameter dictates the number of args required for one element to be
                added to the array.

                If set to 0, the options is treated as a "flag only" option; no value will be
                consumed from the CLI when the user passes this option, and the constructor will be
                called with the value `"True"`. The constructor is never called if the flag isn't
                passed by the user.

                Must be ≥0.

                Variable-length consumption is not supported. To accept a variable number of
                values in a single invocation, use `count=1` and pass the values as a Python
                literal (e.g. `+[1, 2, 3]`). The constructor can then call `plus_literal` or
                `literal` internally and validate the resulting shape.
            repeatable: If `True`, this option can be called multiple times. Raw tokens are
                accumulated into a list and passed to the constructor as a single finalizer call
                after parsing completes. If `count` is greater than 1, each invocation contributes a
                tuple of strings to the list rather than a plain string.
            sticky: If `True`, this option consumes every subsequent token as a value, including
                tokens that look like other flags, until argv is exhausted or a `stickyStopFlag`
                is encountered.
                Warning: because other flags do not stop a sticky option, any options declared
                after it can never be set by the user, unless a `stickyStopFlag` has been set.
            stickyStopFlag: If given (a common value would be `--`), this flag can be used by the
                user to stop a sticky option from consuming tokens.
            exception: If provided, the parser will raise this exception with the value it got from
                the user when this option is encountered.

        Raises:
            DuplicateFlagError: One or more flags are already in use by an existing option.
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
        dict keyed by option name. Array options produce lists; all others produce a single value.

        Args:
            argv: Arguments to parse.

        Returns:
            args: Positional values in declaration order.
            kwargs: Maps flag option names to their values.

        Raises:
            FlagAlreadyPassedError: A non-array flag was passed more than once and
                `allowDuplicates=False`.
            UnrecognizedTokenError: A token did not match any registered flag or positional slot,
                and required options are still outstanding.
            UnexpectedTokenError: A token was encountered after all positionals and required options
                had already been satisfied.
            MissingValueError: argv was exhausted while collecting values for a multi-value option.
            MissingError: One or more required options were not provided.
        """
        # Disclaimer: this function is a bit of a mess. It grew organically through a design
        # iteration and accumulated a few too many responsibilities. The logic is correct,
        # the names are fine, it just... could use a spa day. Soon.
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

            # sticky
            if sticky is not None:
                if sticky.stickyStopFlag and arg == sticky.stickyStopFlag:
                    sticky = None
                    stickyKey = None
                    continue
                option = sticky
                key = stickyKey
                values.append(arg)

            # kwargs
            elif option is not None:
                if option.name in kwargs and not option.repeatable and not self._allowDuplicates:
                    raise FlagAlreadyPassedError(arg, kwargs[option.name])
                sticky = None
                stickyKey = None
                key = option.name
                if option.count == 0:
                    # Value must be of type `str` and must evaluate to `True` when cast to `bool`
                    values = ["True"]

            # args
            elif posIndex < len(self._positionals):
                option = self._positionals[posIndex]
                posIndex += 1
                values.append(arg)

            # unknown
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
                except Exception:
                    raise MissingValueError(option.name, len(values), option.count)
                values.append(value)

            # Collect raw value(s); construction is deferred to after the loop
            raw = tuple(values) if option.count > 1 else values[0]

            # Interrupt options: construct immediately and raise.
            if option.exception is not None:
                raise option.exception(self._construct(option.name, option.constructor, raw))

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
            args[i] = self._construct(option.name, option.constructor, args[i])
        for option in self._options:
            if option.name not in kwargs:
                continue
            kwargs[option.name] = self._construct(
                option.name, option.constructor, kwargs[option.name]
            )

        # Validate
        if missing := self._get_missing(args, kwargs):
            raise MissingOptionError(missing)

        return args, kwargs

    @staticmethod
    def _construct(location: str, constructor: Callable[..., T], value: RawValue) -> T:
        try:
            # If `option.count` does not match the constructor, it is a developer error, not a
            # library error
            return constructor(value)
        except Exception as e:
            raise ConstructionError(location, constructor, value) from e

    def _get_missing(self, args, kwargs) -> list[ParserOption]:
        """Returns required options that have not yet been provided."""
        missing = [o for o in self._options if o.required and o.name not in kwargs]
        if len(args) < len(self._positionals):
            missing.extend([o for o in self._positionals[len(args) :] if o.required])
        return missing

    def _find_option_by_flag(self, flag: str) -> ParserOption | None:
        """Finds an option by flag."""
        caseFunc = str if self._caseSensitive else str.lower
        for option in self._options:
            for optionFlag in option.flags:
                if caseFunc(flag) == caseFunc(optionFlag):
                    return option

    def _validate_duplicate_flags(self, flags: Iterable[str] | None):
        """
        Checks if any of the given flags are already in use by existing options.

        Raises:
            DuplicateFlagError: One or more flags are already in use by an existing option.
        """
        duplicateFlags = []
        for flag in flags or []:
            if self._find_option_by_flag(flag) is not None:
                duplicateFlags.append(flag)
        if duplicateFlags:
            raise DuplicateFlagError(duplicateFlags)
