from typing import Any, Generic, TypeVar

from .._compat import Self
from ._base import ConstructorAbc

# Python < 3.12 (would use variadic generics otherwise)
R = TypeVar("R")


class FlagConstructor(ConstructorAbc[[], R], Generic[R]):
    """
    Constructs a fixed value whenever the flag is passed, consuming no CLI values.

    The value of the flag when it isn't passed is the default of the parameter, so it is never
    selected by annotation; opt into it with `CliConfig(constructor=FlagConstructor())`.
    """

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return False  # A `bool` parameter takes a value unless explicitly made a flag

    def __init__(self, presentValue: R = True) -> None:
        """
        Args:
            presentValue:
                The value the flag constructs when it is passed.
        """
        super().__init__(self._construct, count=0)
        self._presentValue = presentValue

    def _construct(self) -> R:
        """Returns the present value."""
        return self._presentValue

    def __str__(self) -> str:
        return "flag"
