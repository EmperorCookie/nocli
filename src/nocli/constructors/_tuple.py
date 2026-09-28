from collections.abc import Callable, Iterable
from typing import Any

from ._constructor import Constructor


class TupleConstructor(Constructor):
    """Constructs a tuple from a sequence of constructors."""

    def __init__(self, *constructors: Callable[[Any], Any]) -> None:
        """
        Args:
            *constructors:
                The constructors to use for each element of the tuple.
        """
        super().__init__(tuple)
        self._constructors = constructors

    @property
    def count(self) -> int:
        return sum(c.count if isinstance(c, TupleConstructor) else 1 for c in self._constructors)

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (self._constructors,)

    def __call__(self, values: Iterable[Any]) -> tuple[Any, ...]:
        remaining = iter(values)
        result = []
        for constructor in self._constructors:
            if isinstance(constructor, TupleConstructor):
                result.append(constructor(next(remaining) for _ in range(constructor.count)))
            else:
                result.append(constructor(next(remaining)))
        return super().__call__(result)

    def __repr__(self) -> str:
        return f"tuple[{', '.join(str(c) for c in self._constructors)}]"
