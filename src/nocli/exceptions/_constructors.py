from collections.abc import Generator, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from .._compat import Self
from ._base import CliBuildError

if TYPE_CHECKING:
    from ..constructors import ConstructorAbc


class UnsupportedAnnotationError(CliBuildError):
    """A constructor was asked to resolve an annotation that it does not support."""

    def __init__(self, constructor: type["ConstructorAbc"], annotation: Any) -> None:
        """
        Args:
            constructor:
                The constructor class that was asked to resolve the annotation.
            annotation:
                The annotation that the constructor does not support.
        """
        self._constructor = constructor
        self._annotation = annotation
        super().__init__(
            f"Expected an annotation handled by `{self.constructor.__name__}`"
            f"; got `{self.annotation}`"
        )

    @property
    def constructor(self) -> type["ConstructorAbc"]:
        """The constructor class that was unable to resolve the annotation."""
        return self._constructor

    @property
    def annotation(self) -> Any:
        """The annotation that was not supported."""
        return self._annotation


class NoConstructorError(CliBuildError):
    """Unable to find a valid constructor for a given annotation."""

    def __init__(self, annotation: Any) -> None:
        """
        Args:
            annotation:
                The annotation that no constructor handles.
        """
        self._annotation = annotation
        super().__init__(
            f"Expected a constructor for annotation `{self.annotation}`"
            " from `CliConfig.constructor` or a handler in `constructors`; got none"
        )

    @property
    def annotation(self) -> Any:
        """The annotation that no constructor handles."""
        return self._annotation


class ConstructorShapeError(CliBuildError):
    """Constructors that must be combined into a single value consume incompatible CLI values."""

    def __init__(self, constructors: Sequence["ConstructorAbc"], message: str) -> None:
        """
        Args:
            constructors:
                The constructors whose shapes (`count` and `repeatable`) are incompatible.
            message:
                Describes what the combination requires and how the constructors fall short.
        """
        self._constructors = tuple(constructors)
        super().__init__(message)

    @property
    def constructors(self) -> tuple["ConstructorAbc", ...]:
        """The constructors that could not be combined."""
        return self._constructors

    @property
    def constructorsDisplay(self) -> str:
        """The constructors that could not be combined, quoted and comma separated."""
        return ", ".join(f"`{c}`" for c in self.constructors)


class TupleElementShapeError(ConstructorShapeError):
    """Tuple elements are repeatable, but a fixed number of CLI values can't be split across them."""

    def __init__(self, constructors: Sequence["ConstructorAbc"]) -> None:
        """
        Args:
            constructors:
                The repeatable elements.
        """
        self._constructors = tuple(constructors)
        super().__init__(
            constructors,
            f"Expected tuple elements that are not repeatable; got ({self.constructorsDisplay})",
        )


class IterableElementShapeError(ConstructorShapeError):
    """Iterable elements are repeatable, but repetitions can't be nested."""

    def __init__(self, constructor: "ConstructorAbc") -> None:
        """
        Args:
            constructor:
                The repeatable constructor of the elements.
        """
        self._constructors = (constructor,)
        super().__init__(
            [constructor],
            f"Expected iterable elements that are not repeatable; got {self.constructorsDisplay}",
        )


class UnionMemberShapeError(ConstructorShapeError):
    """Union members disagree on the CLI values they consume."""

    def __init__(self, constructors: Sequence["ConstructorAbc"]) -> None:
        """
        Args:
            constructors:
                The members of the union.
        """
        self._constructors = tuple(constructors)
        super().__init__(
            constructors,
            "Expected union members that agree on the CLI values they consume"
            f"; got ({self.shapesDisplay})",
        )

    @property
    def shapesDisplay(self) -> str:
        """The members, each with the CLI values it consumes, quoted and comma separated."""
        return ", ".join(
            f"`{c}`: count={c.count}{', repeatable' if c.repeatable else ''}"
            for c in self.constructors
        )


class UnionConstructionError(ValueError):
    """No member of a union was able to construct the value."""

    @classmethod
    def collector(cls: type[Self], value: Any) -> "_Failures":
        """
        Starts collecting the failures of constructors that are tried in turn on the same value.

        Each attempt runs inside `collector.context(constructor)`, which records and suppresses
        its failure. Once every attempt has failed, `collector.raise_any()` raises this error.

        Args:
            value:
                The value that the constructors are being tried on.

        Returns:
            The collector to run the attempts with.
        """
        return _Failures(value)

    def __init__(self, value: Any, failures: Sequence[tuple["ConstructorAbc", Exception]]) -> None:
        """
        Args:
            value:
                The value that no union member could construct.
            failures:
                Each member that was tried, in order, along with the exception it raised.
        """
        self._value = value
        self._failures = tuple(failures)
        super().__init__(
            f"Expected a value accepted by one of ({self.membersDisplay})"
            f"; got `{self.value}` ({self.reasonsDisplay})"
        )

    @property
    def value(self) -> Any:
        """The value that no union member could construct."""
        return self._value

    @property
    def failures(self) -> tuple[tuple["ConstructorAbc", Exception], ...]:
        """Each member that was tried, in order, along with the exception it raised."""
        return self._failures

    @property
    def membersDisplay(self) -> str:
        """Each member that was tried, quoted and comma separated."""
        return ", ".join(f"`{c}`" for c, _ in self.failures)

    @property
    def reasonsDisplay(self) -> str:
        """Each member that was tried along with why it failed, quoted and comma separated."""
        return ", ".join(f"`{c}`: {e}" for c, e in self.failures)


class _Failures:
    """Collects the exceptions raised by constructors as they are tried in turn."""

    def __init__(self, value: Any) -> None:
        """
        Args:
            value:
                The value that the constructors are being tried on.
        """
        self._value = value
        self._failures: list[tuple[ConstructorAbc, Exception]] = []

    @contextmanager
    def context(self, constructor: "ConstructorAbc") -> Generator[None, None, None]:
        """
        Records and suppresses any `Exception` raised within the block on behalf of `constructor`.

        Every call returns a new context manager, so any number of attempts can be made with the
        same collector, including nested ones.

        Args:
            constructor:
                The constructor being tried.
        """
        try:
            yield
        # Every failure of the constructor is recorded to be reported together, so none can be let
        # through; the blind catch is the purpose of the collector
        except Exception as e:  # noqa: BLE001
            self._failures.append((constructor, e))

    def raise_any(self) -> None:
        """
        Raises `UnionConstructionError` if any failure was recorded; otherwise does nothing.

        Raises:
            UnionConstructionError:
                At least one failure was recorded.
        """
        if self._failures:
            raise UnionConstructionError(self._value, self._failures)
