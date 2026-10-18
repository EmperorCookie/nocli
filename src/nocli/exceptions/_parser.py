from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from ._base import ParserError

if TYPE_CHECKING:
    from .._parser import ParserOption, RawValue


class DuplicateFlagError(ParserError):
    """One or more flags are already in use by an existing option."""

    def __init__(self, flags: list[str]) -> None:
        """
        Args:
            flags:
                The flags that are already in use.
        """
        self._flags = flags
        super().__init__(f"Expected flags that are not in use; got duplicate flags `{self.flags}`")

    @property
    def flags(self) -> list[str]:
        """The flags that are already in use."""
        return self._flags


class FlagAlreadyPassedError(ParserError):
    """A flag has been passed twice and would overwrite a value."""

    def __init__(self, flag: str, value: Any) -> None:
        """
        Args:
            flag:
                The flag that already has a value.
            value:
                The value that would be overwritten.
        """
        self._flag = flag
        self._value = value
        super().__init__(
            "Expected each flag to be passed once"
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

    def __init__(self, name: str, found: int, expected: int) -> None:
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
        super().__init__(f"Expected {self.expected} values for `{self.name}`; got {self.found}")

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

    def __init__(self, token: str) -> None:
        """
        Args:
            token:
                The token that did not match any registered flag or positional slot.
        """
        self._token = token
        super().__init__(f"Expected a registered flag; got `{self.token}`")

    @property
    def token(self) -> str:
        """The unrecognized token."""
        return self._token


class UnexpectedTokenError(ParserError):
    """No more tokens were expected, but a token was found anyway."""

    def __init__(self, token: str) -> None:
        """
        Args:
            token:
                The extra token encountered after all positionals and required options had already
                been satisfied.
        """
        self._token = token
        super().__init__(f"Expected no further tokens; got `{self.token}`")

    @property
    def token(self) -> str:
        """The unexpected token."""
        return self._token


class MissingOptionError(ParserError):
    """One or more required options is missing."""

    def __init__(self, missing: Iterable["ParserOption"]) -> None:
        """
        Args:
            missing:
                The required options that were not provided.
        """
        self._missing = tuple(missing)
        super().__init__(f"Expected values for required options ({self.missingDisplay}); got none")

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

    @property
    def missingDisplay(self) -> str:
        """The first flag or name of each missing option, quoted and comma separated."""
        return ", ".join(f"`{o}`" for o in self.missingFlagsOrNames)


class ConstructionError(ParserError):
    """Failed to parse a user value using the provided constructor."""

    def __init__(
        self,
        location: str,
        constructor: Callable[..., Any],
        value: "RawValue",
        cause: Exception,
    ) -> None:
        """
        Args:
            location:
                The location name where the error occurred.
            constructor:
                The constructor that was used and failed.
            value:
                The user value that was passed to the constructor.
            cause:
                The exception that the constructor raised.
        """
        self._location = location
        self._constructor = constructor
        self._value = value
        self._cause = cause
        super().__init__(
            f"Expected a valid value for `{self.location}`; got `{self.value}`{self.reasonDisplay}"
        )

    @property
    def location(self) -> str:
        """The location name where the error occurred."""
        return self._location

    @property
    def constructor(self) -> Callable[..., Any]:
        """The constructor that was used and failed."""
        return self._constructor

    @property
    def value(self) -> "RawValue":
        """The user value that was passed to the constructor."""
        return self._value

    @property
    def cause(self) -> Exception:
        """The exception that the constructor raised."""
        return self._cause

    @property
    def reason(self) -> str:
        """The message of the exception that the constructor raised; empty if it had none."""
        return str(self.cause)

    @property
    def reasonDisplay(self) -> str:
        """The reason as a message suffix; empty if there is none."""
        return f": {self.reason}" if self.reason else ""
