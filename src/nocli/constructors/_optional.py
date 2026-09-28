from collections.abc import Callable, Collection
from typing import Any, Generic, TypeVar

from ._constructor import Constructor

# Python < 3.12 (would use variadic generics otherwise)
A = TypeVar("A")
R = TypeVar("R")


class OptionalConstructor(Constructor, Generic[A, R]):
    """Constructs any value while treating certain values as `None`."""

    def __init__(
        self,
        constructor: Callable[[A], R],
        *,
        falsyIsNone: bool = True,
        noneValues: Collection[str] | None = None,
        caseSensitive: bool = True,
    ) -> None:
        """
        Args:
            constructor:
                The constructor to wrap.
            falsyIsNull:
                If `True`, a falsy instance is treated as `None`.
            noneValues:
                Other values that should also be converted to `None`.
            caseSensitive:
                If `True`, the comparison with `noneValues` of type `str` is case sensitive.
        """
        super().__init__(constructor)
        self._falsyIsNone = falsyIsNone
        self._caseSensitive = caseSensitive
        self._noneValues = frozenset(self._set_case(o) for o in (noneValues or tuple()))

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (*super()._eqFields, self._falsyIsNone, self._noneValues, self._caseSensitive)

    def _set_case(self, value: Any) -> Any:
        c = str if self._caseSensitive else str.lower
        if isinstance(value, str):
            return c(value)
        return value

    def __call__(self, value: A) -> R | None:
        if self._falsyIsNone and not value:
            return None
        if self._set_case(value) in self._noneValues:
            return None
        return super().__call__(value)
