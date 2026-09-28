from collections.abc import Callable, Iterable
import math
from typing import Any

from ._constructor import Constructor


def is_positive(value: float) -> bool:
    return value > 0


class BoolConstructor(Constructor):
    """A constructor for boolean values with configurable options for `True` and `False`."""

    def __init__(
        self,
        trueOptions: Iterable[str] = ("yes", "y", "true", "t", "on"),
        falseOptions: Iterable[str] = ("no", "n", "false", "f", "off"),
        *,
        floatPredicate: Callable[[float], bool] | None = is_positive,
        invalid: bool | None = None,
        caseSensitive: bool = False,
    ) -> None:
        """
        Args:
            trueOptions:
                Strings that resolve to `True`.
            falseOptions:
                Strings that resolve to `False`.
            floatPredicate:
                If set, numeric strings are parsed as floats and the result is passed to this
                predicate to determine truthiness; takes priority over `trueOptions`/`falseOptions`.
                Note that `inf`, `-inf`, and `nan` are passed to the string matching options and are
                not treated as floats.
            invalid:
                Defines the default value for unrecognized inputs. If `None`, unrecognized inputs
                raise a `ValueError`.
            caseSensitive:
                If `True`, matching against `trueOptions` and `falseOptions` is case-sensitive.
        """
        super().__init__(bool)
        self._trueOptions = tuple(trueOptions)
        self._falseOptions = tuple(falseOptions)
        self._invalid = invalid
        self._floatPredicate = floatPredicate
        self._caseSensitive = caseSensitive
        self._trueLookup = frozenset((o if caseSensitive else o.lower()) for o in self._trueOptions)
        self._falseLookup = frozenset(
            (o if caseSensitive else o.lower()) for o in self._falseOptions
        )

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (
            self._trueOptions,
            self._falseOptions,
            self._invalid,
            self._floatPredicate,
            self._caseSensitive,
        )

    def __call__(self, value: str) -> bool:
        if self._floatPredicate is not None:
            try:
                f = float(value)
            except ValueError:
                pass
            else:
                if math.isfinite(f):
                    return super().__call__(self._floatPredicate(f))
        option = value if self._caseSensitive else value.lower()
        if option in self._trueLookup:
            return True
        if option in self._falseLookup:
            return False
        if self._invalid is None:
            raise ValueError(
                f"Expected one of"
                f" ({', '.join(f'`{o}`' for o in (self._trueOptions + self._falseOptions))})"
                f"; got `{value}`"
            )
        return self._invalid
