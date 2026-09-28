from collections.abc import Callable
from typing import Any, Generic, ParamSpec, TypeVar

# Python < 3.12 (would use variadic generics otherwise)
A = ParamSpec("A")
R = TypeVar("R")


class Constructor(Generic[A, R]):
    """A callable that converts arbitrary values into a final value."""

    def __init__(self, constructor: Callable[A, R]) -> None:
        """
        Args:
            constructor:
                Function that converts string values into a final value.
        """
        self._constructor = constructor

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        """Fields that will be used for equality check."""
        return (self._constructor,)

    def __call__(self, *args: A.args, **kwargs: A.kwargs) -> R:
        return self._constructor(*args, **kwargs)

    def __eq__(self, other: "Constructor") -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._eqFields == other._eqFields

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{self._eqFields}"
