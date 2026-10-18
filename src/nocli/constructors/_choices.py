from collections.abc import Callable, Generator
from enum import Enum
from typing import Any, Generic, Literal, TypeVar, get_args, get_origin

from .._compat import Self
from ..exceptions import UnsupportedAnnotationError
from ._base import ConstructorAbc

# Python < 3.12 (would use variadic generics otherwise)
R = TypeVar("R")
E = TypeVar("E", bound=Enum)  # The enum whose members are the choices


class ChoicesConstructor(ConstructorAbc[[str], R], Generic[R]):
    """
    Accepts only a fixed set of values, optionally turning the chosen one into something else.

    Handles `Literal[...]` and `Enum` annotations, where an enum is chosen by member name.
    """

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, ConstructorAbc[..., Any], ConstructorAbc[..., Any]]:
        handler = cls._get_handler(annotation)
        if handler is None:
            raise UnsupportedAnnotationError(cls, annotation)
        yield from ()
        return handler(annotation)

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return cls._get_handler(annotation) is not None

    @classmethod
    def from_enum(
        cls: "type[ChoicesConstructor[Any]]", enum: type[E], *, caseSensitive: bool = True
    ) -> "ChoicesConstructor[E]":
        """
        Builds a constructor that chooses a member of an enum by its name.

        Args:
            enum:
                The enum whose members are the choices.
            caseSensitive:
                If `True`, member names are matched case-sensitively.

        Returns:
            A constructor whose result is the chosen enum member.
        """
        return cls(*enum._member_names_, finalizer=enum.__getitem__, caseSensitive=caseSensitive)

    @classmethod
    def _get_handler(
        cls: "type[ChoicesConstructor[Any]]", annotation: Any
    ) -> "Callable[[Any], ChoicesConstructor[Any]] | None":
        """Returns the function that builds a constructor for the annotation, if supported."""
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return cls._handle_enum
        if get_origin(annotation) is Literal:
            return cls._handle_literal
        return None

    @classmethod
    def _handle_enum(
        cls: "type[ChoicesConstructor[Any]]", annotation: type[Enum]
    ) -> "ChoicesConstructor[Any]":
        """Builds a constructor for an `Enum` annotation."""
        return cls.from_enum(annotation)

    @classmethod
    def _handle_literal(
        cls: "type[ChoicesConstructor[Any]]", annotation: Any
    ) -> "ChoicesConstructor[Any]":
        """Builds a constructor for a `Literal` annotation."""
        values = get_args(annotation)
        return cls(*values)

    def __init__(
        self, *choices: str, finalizer: Callable[[str], R] = str, caseSensitive: bool = True
    ) -> None:
        """
        Args:
            *choices:
                The values that are accepted, in the order they are shown. Duplicates are ignored.
            finalizer:
                Converts the chosen value into the final value.
            caseSensitive:
                If `True`, the input is matched against the choices case-sensitively. Otherwise,
                the choice as declared is what gets finalized.
        """
        super().__init__(self._construct)
        self._choices = tuple(dict.fromkeys(choices))  # Declaration order, without duplicates
        self._finalizer = finalizer
        self._caseSensitive = caseSensitive

    @property
    def _lookup(self) -> dict[str, str]:
        """The choices as declared, by the key they are compared with."""
        return {self._set_case(c): c for c in self._choices}

    def _construct(self, value: str) -> R:
        """Returns the finalized choice that matches the value, or raises if there is none."""
        if (key := self._set_case(value)) in self._lookup:
            return self._finalizer(self._lookup[key])
        raise ValueError(
            f"Expected one of ({', '.join(f'`{c}`' for c in self._choices)}); got `{value}`"
        )

    def _set_case(self, value: str) -> str:
        """Normalizes a value for comparison according to `caseSensitive`."""
        return (str if self._caseSensitive else str.lower)(value)

    def __str__(self) -> str:
        choices = " | ".join(repr(c) for c in self._choices)
        # Case sensitivity is the expectation, so only the exception is spelled out
        return choices if self._caseSensitive else f"choices<ins>[{choices}]"
