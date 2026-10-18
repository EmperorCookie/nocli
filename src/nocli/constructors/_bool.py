import math
from collections.abc import Callable, Generator, Iterable
from typing import Any, Generic, TypeVar

from .._compat import Self
from ..exceptions import UnsupportedAnnotationError
from ._base import ConstructorAbc

# Python < 3.12 (would use variadic generics otherwise)
R = TypeVar("R")


def is_positive(value: float) -> bool:
    """
    Checks whether a number is greater than zero.

    Args:
        value:
            The number that a numeric string was parsed as.

    Returns:
        `True` if the number is greater than zero.
    """
    return value > 0


class BoolConstructor(ConstructorAbc[[str], R], Generic[R]):
    """A constructor for boolean values with configurable options for `True` and `False`."""

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, ConstructorAbc[..., Any], ConstructorAbc[..., Any]]:
        if not cls.can_handle(annotation):
            raise UnsupportedAnnotationError(cls, annotation)
        yield from ()
        return cls(finalizer=annotation)

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return isinstance(annotation, type) and issubclass(annotation, bool)

    def __init__(
        self,
        trueOptions: Iterable[str] = ("yes", "y", "true", "t", "on"),
        falseOptions: Iterable[str] = ("no", "n", "false", "f", "off"),
        *,
        finalizer: Callable[[Any], R] = bool,
        floatPredicate: Callable[[float], bool] | None = is_positive,
        invalidFinalizer: Callable[[Any], R] | None = None,
        caseSensitive: bool = False,
    ) -> None:
        """
        Args:
            trueOptions:
                Strings that resolve to `True`.
            falseOptions:
                Strings that resolve to `False`.
            finalizer:
                Converts the `bool` that was determined into the final value.
            floatPredicate:
                If set, numeric strings are parsed as floats and the result is passed to this
                predicate to determine truthiness; takes priority over `trueOptions`/`falseOptions`.
                Note that `inf`, `-inf`, and `nan` are passed to the string matching options and are
                not treated as floats.
            invalidFinalizer:
                Converts an unrecognized input into the final value, so that it doesn't raise. For
                example, `lambda _: False` resolves anything unrecognized to `False`. If `None`,
                unrecognized inputs raise a `ValueError`.
            caseSensitive:
                If `False`, matching against `trueOptions` and `falseOptions` ignores case.
        """
        super().__init__(self._construct)
        self._trueOptions = tuple(trueOptions)
        self._falseOptions = tuple(falseOptions)
        self._finalizer = finalizer
        self._invalidFinalizer = invalidFinalizer
        self._floatPredicate = floatPredicate
        self._caseSensitive = caseSensitive

    @property
    def _trueLookup(self) -> frozenset[str]:
        """The options that resolve to `True`, as they are compared."""
        return frozenset((o if self._caseSensitive else o.lower()) for o in self._trueOptions)

    @property
    def _falseLookup(self) -> frozenset[str]:
        """The options that resolve to `False`, as they are compared."""
        return frozenset((o if self._caseSensitive else o.lower()) for o in self._falseOptions)

    def _construct(self, value: str) -> R:
        """Determines the boolean for the value, then finalizes it."""
        if self._floatPredicate is not None:
            try:
                f = float(value)
            except ValueError:
                pass
            else:
                if math.isfinite(f):
                    return self._finalizer(self._floatPredicate(f))
        option = value if self._caseSensitive else value.lower()
        if option in self._trueLookup:
            return self._finalizer(True)
        if option in self._falseLookup:
            return self._finalizer(False)
        if self._invalidFinalizer is None:
            raise ValueError(
                "Expected one of"
                f" ({', '.join(f'`{o}`' for o in (self._trueOptions + self._falseOptions))})"
                f"; got `{value}`"
            )
        return self._invalidFinalizer(value)

    def __str__(self) -> str:
        return "bool"
