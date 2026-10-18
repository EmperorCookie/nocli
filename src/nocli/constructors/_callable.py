from collections.abc import Callable, Generator
from typing import Any, ParamSpec, TypeVar, get_origin

from .._compat import Self
from ..exceptions import UnsupportedAnnotationError
from ._base import ConstructorAbc

# Python < 3.12 (would use variadic generics otherwise)
A = ParamSpec("A")  # The signature of the wrapped callable
R = TypeVar("R")  # What the wrapped callable returns


class CallableConstructor(ConstructorAbc[A, R]):
    """
    Wraps any plain callable; the catch-all for annotations that are callable themselves.

    The callable is given a string, unless `count` says that it takes several (a tuple of strings)
    or none (no arguments at all). If it is `repeatable`, it is given a list of whatever each
    occurrence would be given, which is a list of empty tuples for `count=0`. Its signature is the
    signature of this constructor, so a subclass that adjusts how it is called states that
    signature explicitly (e.g. `CallableConstructor[[str], int]`).
    """

    @staticmethod
    def coerce(constructor: Callable[..., Any]) -> ConstructorAbc[..., Any]:
        """
        Makes sure a constructor is a `ConstructorAbc`, so that it can describe how it consumes CLI
        values and how it is displayed.

        Args:
            constructor:
                A constructor, or a plain callable that consumes a single value.

        Returns:
            `constructor` itself if it already is a `ConstructorAbc`; otherwise a
            `CallableConstructor` wrapping it.
        """
        if isinstance(constructor, ConstructorAbc):
            return constructor
        return CallableConstructor(constructor)

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, ConstructorAbc[..., Any], ConstructorAbc[..., Any]]:
        if not cls.can_handle(annotation):
            raise UnsupportedAnnotationError(cls, annotation)
        yield from ()
        return cls(annotation)

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return callable(annotation) and get_origin(annotation) is None

    def __init__(
        self,
        constructor: Callable[A, R],
        *,
        displayType: str | None = None,
        repeatable: bool = False,
        count: int = 1,
    ) -> None:
        """
        Args:
            constructor:
                The callable to wrap.
            displayType:
                Overrides the type label shown for this constructor in help output. Defaults to
                the name of `constructor`.
            repeatable:
                See `ConstructorAbc`.
            count:
                See `ConstructorAbc`.
        """
        super().__init__(constructor, repeatable=repeatable, count=count)
        self._displayType = displayType

    def __str__(self) -> str:
        if self._displayType is not None:
            return self._displayType
        return getattr(self._constructor, "__name__", repr(self._constructor))
