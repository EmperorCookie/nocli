import ast
from typing import Any

from ._constructor import Constructor


class LiteralEvalConstructor(Constructor):
    """Constructs a Python literal from a string."""

    def __init__(self, *, plus: bool = False) -> None:
        """
        Args:
            plus:
                If `True`, a regular string will be returned instead of a literal unless the input
                starts with a `+`.

                In `plus` mode, use `\\+` for a string that begins with `+`, and `\\\\` for a string
                that begins with `\\`. Beyond the first character in those specific cases, nothing
                else needs to be escaped.
        """
        super().__init__(ast.literal_eval)
        self._plus = plus

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (*super()._eqFields, self._plus)

    def __call__(self, value: str) -> Any:
        if self._plus:
            if value.startswith("\\"):
                return value[1:]
            if not value.startswith("+"):
                return value
            return super().__call__(value[1:])
        # Using `str` to avoid an `AST` from being passed straight through
        return super().__call__(str(value))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}{'<plus>' if self._plus else ''}"
