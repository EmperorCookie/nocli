from collections.abc import Callable
from enum import Enum
from typing import Any, Generic, TypeVar

from ._constructor import Constructor

# Python < 3.12 (would use variadic generics otherwise)
R = TypeVar("R")
C = TypeVar("C", bound="ChoicesConstructor")


class ChoicesConstructor(Constructor, Generic[R]):
    def __init__(
        self, *choices: str, constructor: Callable[[str], R] = str, caseSensitive: bool = True
    ) -> None:
        super().__init__(constructor)
        self._choices = frozenset(choices)
        self._caseSensitive = caseSensitive
        self._lookup = {self._set_case(c): c for c in self._choices}

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (*super()._eqFields, self._choices, self._caseSensitive)

    @classmethod
    def from_enum(cls: type[C], enum: type[Enum], *, caseSensitive: bool = True) -> C:
        return cls(*enum._member_names_, constructor=enum.__getitem__, caseSensitive=caseSensitive)

    def _set_case(self, value: str) -> str:
        return (str if self._caseSensitive else str.lower)(value)

    def __call__(self, value: str) -> R:
        if (key := self._set_case(value)) in self._lookup:
            return super().__call__(self._lookup[key])
        raise ValueError(
            f"Expected one of ({', '.join(f'`{c}`' for c in self._choices)}); got `{value}`"
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}<{'sen' if self._caseSensitive else 'ins'}>"
            f"[{', '.join(f'`{c}`' for c in sorted(self._choices))}]"
        )
