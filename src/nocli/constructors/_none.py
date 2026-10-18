from collections.abc import Collection, Generator
from types import NoneType
from typing import Any

from .._compat import Self
from ..exceptions import UnsupportedAnnotationError
from ._base import ConstructorAbc


class NoneConstructor(ConstructorAbc[[str], None]):
    """
    Constructs `None` from an empty value or an explicitly none-mapped value, and rejects
    everything else.
    """

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, ConstructorAbc[..., Any], ConstructorAbc[..., Any]]:
        if not cls.can_handle(annotation):
            raise UnsupportedAnnotationError(cls, annotation)
        yield from ()
        return cls()

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return annotation is None or annotation is NoneType

    def __init__(
        self,
        *,
        falsyIsNone: bool = True,
        noneValues: Collection[str] | None = None,
        caseSensitive: bool = True,
    ) -> None:
        """
        Args:
            falsyIsNone:
                If `True`, a falsy value (e.g. an empty string) is treated as `None`.
            noneValues:
                Other values that should also be treated as `None`.
            caseSensitive:
                If `True`, the comparison with `noneValues` of type `str` is case sensitive.
        """
        super().__init__(self._construct)
        self._falsyIsNone = falsyIsNone
        self._caseSensitive = caseSensitive
        self._noneValues = tuple(noneValues or ())

    @property
    def _noneLookup(self) -> frozenset[Any]:
        """The values that resolve to `None`, as they are compared."""
        return frozenset(self._set_case(o) for o in self._noneValues)

    def _construct(self, value: str) -> None:
        """Resolves the value to `None`, or raises `ValueError` if the value is not none-mapped."""
        if self._falsyIsNone and not value:
            return
        if self._set_case(value) in self._noneLookup:
            return
        raise ValueError(f"Expected an empty value to resolve to `None`; got `{value}`")

    def _set_case(self, value: Any) -> Any:
        """Normalizes a value for `noneValues` comparison according to `caseSensitive`."""
        c = str if self._caseSensitive else str.lower
        if isinstance(value, str):
            return c(value)
        return value

    def __str__(self) -> str:
        return "None"
