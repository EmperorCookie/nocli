from collections.abc import Callable, Iterable
from typing import Any, Generic, TypeVar

from ._constructor import Constructor

# Python < 3.12 (would use variadic generics otherwise)
A = TypeVar("A")
N = TypeVar("N")
R = TypeVar("R")


class IterableConstructor(Constructor, Generic[A, N, R]):
    """
    Constructs any value from an iterable of values, each of which is constructed by a nested
    constructor.
    """

    def __init__(
        self,
        constructor: Callable[[Iterable[N]], R],
        nested: Callable[[A], N],
        *,
        minItems: int | None = None,
        maxItems: int | None = None,
    ) -> None:
        """
        Args:
            constructor:
                The constructor to use for the entire iterable.
            nested:
                The constructor to use for individual elements of the iterable.
            minItems:
                The minimum number of elements that must be present in the iterable.
            maxItems:
                The maximum number of elements that may be present in the iterable.
        """
        super().__init__(constructor)
        self._nested = nested
        self._minItems = minItems
        self._maxItems = maxItems

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (*super()._eqFields, self._nested)

    def __call__(self, values: Iterable[A]) -> R:
        result = super().__call__((self._nested(v) for v in values))
        if self._minItems is not None and len(result) < self._minItems:
            raise ValueError(f"Expected at least {self._minItems} items; got {len(result)}")
        if self._maxItems is not None and len(result) > self._maxItems:
            raise ValueError(f"Expected at most {self._maxItems} items; got {len(result)}")
        return result

    def __repr__(self) -> str:
        return f"{self._constructor}[{self._nested}]"
