import ast
from typing import Any

from .._compat import Self
from ._callable import CallableConstructor


class LiteralEvalConstructor(CallableConstructor[[str], Any]):
    """Constructs a Python literal from a string."""

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return False  # Literal evaluation is never an implied behavior

    def __init__(self, *, plus: bool = False) -> None:
        """
        Args:
            plus:
                If `False`, the input is evaluated as a Python literal. In `plus` mode, a regular
                string is returned instead of a literal unless the input starts with a `+`.

                In `plus` mode, use `\\+` for a string that begins with `+`, and `\\\\` for a string
                that begins with `\\`. Beyond the first character in those specific cases, nothing
                else needs to be escaped.
        """
        super().__init__(self._construct)
        self._plus = plus

    def _construct(self, value: str) -> Any:
        """
        Evaluates a string as a Python literal.

        Raises:
            ValueError:
                The string to evaluate is not a literal.
            SyntaxError:
                The string to evaluate is not valid Python.
        """
        if self._plus:
            if value.startswith("\\"):
                return value[1:]
            if not value.startswith("+"):
                return value
            return ast.literal_eval(value[1:])
        # Using `str` to avoid an `AST` from being passed straight through
        return ast.literal_eval(str(value))

    def __str__(self) -> str:
        return f"{type(self).__name__}{'<plus>' if self._plus else ''}"
