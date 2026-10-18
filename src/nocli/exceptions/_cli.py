import inspect
from typing import TYPE_CHECKING, Any

from ._base import CliBuildError

if TYPE_CHECKING:
    from ..constructors import ConstructorAbc


class ConfigConflictError(CliBuildError):
    """A `CliConfig` member would be silently ignored because the constructor owns that behavior."""

    def __init__(
        self, parameter: str, member: str, value: Any, constructor: "ConstructorAbc"
    ) -> None:
        """
        Args:
            parameter:
                Name of the parameter whose config conflicts with its constructor.
            member:
                Name of the `CliConfig` member that would be ignored.
            value:
                The value the `CliConfig` member was set to.
            constructor:
                The constructor that owns the behavior.
        """
        self._parameter = parameter
        self._member = member
        self._value = value
        self._constructor = constructor
        super().__init__(
            f"Parameter `{self.parameter}`: Expected `CliConfig.{self.member}` to be unset for"
            f" constructor `{self.constructor}`, which owns it; got `{self.value}`"
        )

    @property
    def parameter(self) -> str:
        """Name of the parameter whose config conflicts with its constructor."""
        return self._parameter

    @property
    def member(self) -> str:
        """Name of the `CliConfig` member that would be ignored."""
        return self._member

    @property
    def value(self) -> Any:
        """The value the `CliConfig` member was set to."""
        return self._value

    @property
    def constructor(self) -> "ConstructorAbc":
        """The constructor that owns the behavior."""
        return self._constructor


class ParamConstructorError(CliBuildError):
    """A parameter's type annotation is unable to produce a constructor."""

    def __init__(self, parameter: str, cause: CliBuildError) -> None:
        """
        Args:
            parameter:
                Name of the parameter whose type annotation is unable to produce a constructor.
            cause:
                The error that the constructors raised while resolving the annotation.
        """
        self._parameter = parameter
        self._cause = cause
        super().__init__(f"Parameter `{self.parameter}`: {self.cause.message}")

    @property
    def parameter(self) -> str:
        """Name of the parameter whose type annotation is unable to produce a constructor."""
        return self._parameter

    @property
    def cause(self) -> CliBuildError:
        """The error that the constructors raised while resolving the annotation."""
        return self._cause


class ParamNameError(CliBuildError):
    """A parameter is unable to produce a usable name."""

    def __init__(self, parameter: str, reason: str) -> None:
        """
        Args:
            parameter:
                Name of the parameter that is unable to produce a usable name.
            reason:
                Why the parameter is unable to produce a usable name.
        """
        self._parameter = parameter
        self._reason = reason
        super().__init__(f"Parameter `{self.parameter}`: {self.reason}")

    @property
    def parameter(self) -> str:
        """Name of the parameter that is unable to produce a usable name."""
        return self._parameter

    @property
    def reason(self) -> str:
        """Why the parameter is unable to produce a usable name."""
        return self._reason


class InvalidNameError(ParamNameError):
    """A display name, flag or alias has no words to build a name from."""

    def __init__(self, parameter: str, name: str) -> None:
        """
        Args:
            parameter:
                Name of the parameter that has the unusable name.
            name:
                The unusable display name, flag or alias.
        """
        self._name = name
        super().__init__(parameter, f"Expected a name with at least one word; got `{self.name}`")

    @property
    def name(self) -> str:
        """The unusable display name, flag or alias."""
        return self._name


class NoFlagsError(ParamNameError):
    """An option would end up without any flag for the user to pass."""

    def __init__(self, parameter: str) -> None:
        """
        Args:
            parameter:
                Name of the parameter that would have no flags.
        """
        super().__init__(
            parameter,
            "Expected at least one flag from `flags`, `aliases` or `defaultFlags`; got none",
        )


class UnsupportedParameterError(CliBuildError):
    """A parameter of the wrapped function cannot be exposed on the command line."""

    def __init__(self, parameter: str, kind: inspect._ParameterKind) -> None:
        """
        Args:
            parameter:
                Name of the parameter that is not supported.
            kind:
                How the parameter is declared in the signature, e.g. `*args` or `**kwargs`.
        """
        self._parameter = parameter
        self._kind = kind
        super().__init__(
            f"Parameter `{self.parameter}`: Expected a named parameter"
            f"; got a {self.kind.description} parameter"
        )

    @property
    def parameter(self) -> str:
        """Name of the parameter that is not supported."""
        return self._parameter

    @property
    def kind(self) -> inspect._ParameterKind:
        """How the parameter is declared in the signature."""
        return self._kind
