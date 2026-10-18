from collections.abc import Callable, Collection
from typing import Any, Generic, TypeVar

from .._compat import Self
from ._none import NoneConstructor
from ._union import UnionConstructor

# Python < 3.12 (would use variadic generics otherwise)
R = TypeVar("R")  # What the wrapped constructor constructs


class OptionalConstructor(UnionConstructor["R | None"], Generic[R]):
    """
    Constructs any value while treating certain values as `None`.

    Equivalent to a `UnionConstructor` with a `NoneConstructor` ahead of the wrapped constructor,
    which is also what the annotation `None | T` resolves to. Never selected by annotation; use it
    explicitly to configure which values are `None`.
    """

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return False  # `None | T` is a union, and is resolved as such

    def __init__(
        self,
        constructor: Callable[[Any], R],
        *,
        falsyIsNone: bool = True,
        noneValues: Collection[str] | None = None,
        caseSensitive: bool = True,
    ) -> None:
        """
        Args:
            constructor:
                The constructor to wrap.
            falsyIsNone:
                If `True`, a falsy value (e.g. an empty string) is treated as `None`.
            noneValues:
                Other values that should also be treated as `None`.
            caseSensitive:
                If `True`, the comparison with `noneValues` of type `str` is case sensitive.

        Raises:
            UnionMemberShapeError:
                `constructor` does not consume a single CLI value.
        """
        super().__init__(
            NoneConstructor(
                falsyIsNone=falsyIsNone, noneValues=noneValues, caseSensitive=caseSensitive
            ),
            constructor,
        )
