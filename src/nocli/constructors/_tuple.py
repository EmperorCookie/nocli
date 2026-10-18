import sys
from collections.abc import Callable, Generator
from itertools import islice
from typing import Any, Generic, get_args, get_origin

from .._compat import Self
from ..exceptions import TupleElementShapeError, UnsupportedAnnotationError
from ._base import ConstructorAbc, Raw
from ._callable import CallableConstructor

if sys.version_info >= (3, 13):
    from typing import TypeVar
else:
    from typing_extensions import TypeVar  # Python < 3.13 (`TypeVar` has no `default` before 3.13)

# The type of the tuple that is constructed; see `TupleConstructor`
Whole = TypeVar("Whole", bound=tuple[Any, ...], default=tuple[Any, ...])


class TupleConstructor(ConstructorAbc[[Raw], Whole], Generic[Whole]):
    """
    Constructs a tuple of a fixed length, where each element is constructed by its own constructor.

    Consumes as many CLI values as its elements do in total. Handles fixed length tuple annotations
    like `tuple[int, str]`.

    The type argument is the type of the tuple that is constructed. It cannot be inferred from the
    element constructors, so write it explicitly for precise types, e.g.
    `TupleConstructor[tuple[str, int]](str, int)`; it is `tuple[Any, ...]` otherwise. It is not
    checked against the element constructors.

    Elements given as plain callables are used as they are: the constructors that `Cli` uses for
    type hints don't apply to them, so `bool` is the builtin `bool`, not a `BoolConstructor`. To
    have them apply, derive the element with `ConstructorAbc.from_annotation`.
    """

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, ConstructorAbc[..., Any], ConstructorAbc[..., Any]]:
        if not cls.can_handle(annotation):
            raise UnsupportedAnnotationError(cls, annotation)
        elements = []
        for arg in get_args(annotation):
            elements.append((yield arg))
        return cls(*elements)

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        # `tuple[X, ...]` is of arbitrary length, which is for the iterable constructor to handle
        return (
            get_origin(annotation) is tuple
            and bool(args := get_args(annotation))
            and ... not in args
        )

    def __init__(self, *constructors: Callable[..., Any]) -> None:
        """
        Args:
            *constructors:
                The constructors to use for each element of the tuple.

        Raises:
            TupleElementShapeError:
                A constructor is repeatable; a fixed number of CLI values can't be split across a
                variable number of repetitions.
        """
        elements = tuple(CallableConstructor.coerce(c) for c in constructors)
        if repeatable := [c for c in elements if c.repeatable]:
            raise TupleElementShapeError(repeatable)
        super().__init__(self._construct, count=sum(c.count for c in elements))
        self._constructors = elements

    def _construct(self, values: Raw = ()) -> Any:
        """
        Distributes the raw values across the element constructors, in order.

        Elements that consume no CLI values are not given any of the values.
        """
        # A single value arrives as a plain string rather than a tuple of strings
        remaining = iter((values,) if isinstance(values, str) else values)
        result = []
        for constructor in self._constructors:
            if constructor.count == 0:
                result.append(constructor())
            elif constructor.count == 1:
                result.append(constructor(next(remaining)))
            else:
                result.append(constructor(tuple(islice(remaining, constructor.count))))
        return tuple(result)

    def __str__(self) -> str:
        # Parenthesized, as in Python, to be told apart from the brackets of a parent such as an
        # iterable, and from a union
        elements = ", ".join(str(c) for c in self._constructors)
        return f"({elements}{',' if len(self._constructors) == 1 else ''})"
