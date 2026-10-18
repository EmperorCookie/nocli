import warnings
from collections.abc import Callable, Generator, Iterable
from types import NoneType, UnionType
from typing import Any, Generic, TypeVar, Union, get_args, get_origin

from .._compat import Self
from ..exceptions import (
    UnionConstructionError,
    UnionMemberShapeError,
    UnsupportedAnnotationError,
)
from ._base import ConstructorAbc, Raw
from ._callable import CallableConstructor

# Python < 3.12 (would use variadic generics otherwise)
R = TypeVar("R")  # What the members of a union construct


class UnionConstructor(ConstructorAbc[[Raw | Iterable[Raw]], R], Generic[R]):
    """
    Tries each constructor in declaration order, returning the first result that succeeds.

    All of the constructors must consume the same number of CLI values, and be equally repeatable.
    If none of them succeeds, the failure of each is reported in a `UnionConstructionError`.

    Members that consume no CLI values (`count=0`) have nothing to tell them apart by, so the first
    one that doesn't raise is always chosen; a `UserWarning` points that out.

    Handles union annotations like `int | str`. A `None` anywhere but first is never parsed, as it
    means "or do nothing", so `int | None` is just `int`. A leading `None` is parsed first, so
    `None | int` treats an empty value as `None`.

    Members given as plain callables are used as they are: the constructors that `Cli` uses for
    type hints don't apply to them, so `bool` is the builtin `bool`, not a `BoolConstructor`. To
    have them apply, derive the member with `ConstructorAbc.from_annotation`.
    """

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, ConstructorAbc[..., Any], ConstructorAbc[..., Any]]:
        if not cls.can_handle(annotation):
            raise UnsupportedAnnotationError(cls, annotation)
        # A `None` anywhere but first means "or do nothing": the option is simply absent, so there
        # is never anything to parse. A leading `None` is parsed like any other member, ahead of
        # the others
        members = [
            arg for i, arg in enumerate(get_args(annotation)) if not (i > 0 and arg is NoneType)
        ]
        resolved = []
        for member in members:
            resolved.append((yield member))
        if len(resolved) == 1:
            return resolved[0]
        return cls(*resolved)

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return get_origin(annotation) in (Union, UnionType)

    def __init__(self, *constructors: Callable[..., R]) -> None:
        """
        Args:
            *constructors:
                The constructors to try, in the order they should be tried. All of them must agree
                on `count` and `repeatable`. The result is whatever one of them constructs.

        Raises:
            ValueError:
                No constructors were given.
            UnionMemberShapeError:
                The constructors disagree on `count` or `repeatable`.
        """
        if not constructors:
            raise ValueError("Expected at least one constructor; got none")
        members = tuple(CallableConstructor.coerce(c) for c in constructors)
        shapes = {(c.count, c.repeatable) for c in members}
        if len(shapes) > 1:
            raise UnionMemberShapeError(members)
        count, repeatable = next(iter(shapes))
        if count == 0 and not repeatable:
            warnings.warn(
                "Expected union members that consume CLI values to tell them apart"
                f"; got members that consume none, so `{members[0]}` is always chosen"
                " unless it raises",
                stacklevel=2,
            )
        super().__init__(self._construct, repeatable=repeatable, count=count)
        self._constructors = members

    def _construct(self, value: Raw | Iterable[Raw] = ()) -> R:
        """
        Returns the result of the first member to succeed.

        Members that consume no CLI values are not given the value.
        """
        failures = UnionConstructionError.collector(value)
        for constructor in self._constructors:
            with failures.context(constructor):
                if self.count == 0 and not self.repeatable:
                    return constructor()
                return constructor(value)
        failures.raise_any()
        raise RuntimeError("Expected at least one member to have been tried; got none")

    def __str__(self) -> str:
        return " | ".join(str(c) for c in self._constructors)
