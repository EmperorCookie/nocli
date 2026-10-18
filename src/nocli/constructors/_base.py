from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from typing import Any, Generic, ParamSpec, TypeVar

from .._compat import Self
from ..exceptions import NoConstructorError, UnsupportedAnnotationError

# What the parser hands to a constructor: a single string, or several strings for a count above one
Raw = str | tuple[str, ...]

# Python < 3.12 (would use variadic generics otherwise)
A = ParamSpec("A")
R = TypeVar("R")


class ConstructorAbc(ABC, Generic[A, R]):
    """
    A callable that converts arbitrary values into a final value.

    A constructor also describes how it is used: how many CLI values it consumes (`count`), whether
    the option accumulates repeated values (`repeatable`), and how it is shown in help (`__str__`).
    It also decides for itself which type annotations it handles, so that `Cli` can derive one from
    a type hint. To write your own, implement `can_handle` (constructors that are only ever used
    explicitly return `False`) and, if it ever claims an annotation, `resolve`. See
    `from_annotation` for how they are used.
    """

    @staticmethod
    def from_annotation(
        annotation: Any, *constructors: type["ConstructorAbc[..., Any]"]
    ) -> "ConstructorAbc[..., Any]":
        """
        Derives a fully resolved constructor from an annotation.

        Each constructor class is asked in order whether it handles the annotation, and the first
        one that does resolves it. Nested annotations that it asks for are derived the same way,
        from the same constructors. The result is not restricted to the class this is called on;
        `constructors` is the only source of handlers.

        This is also how to have those handlers apply to a constructor that is composed by hand,
        whose plain callables are otherwise used as they are, e.g.
        `IterableConstructor(ConstructorAbc.from_annotation(bool, *nocli.DEFAULT_CONSTRUCTORS))`.

        Args:
            annotation:
                The type annotation to derive a constructor for.
            *constructors:
                The constructor classes that may handle annotations, in the order they are asked.

        Returns:
            The fully resolved constructor.

        Raises:
            NoConstructorError:
                No constructor handles `annotation`, or a nested annotation that was asked for.
        """
        for constructor in constructors:
            if constructor.can_handle(annotation):
                steps = constructor.resolve(annotation)
                try:
                    request = next(steps)
                    while True:
                        request = steps.send(ConstructorAbc.from_annotation(request, *constructors))
                except StopIteration as done:
                    return done.value
        raise NoConstructorError(annotation)

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, "ConstructorAbc[..., Any]", "ConstructorAbc[..., Any]"]:
        """
        Resolves an annotation into a fully resolved constructor.

        The generator yields nested annotations in turn, each of which the caller resolves
        recursively and sends back to the generator; the constructor it returns must be fully
        resolved, built from those results. It may be a simpler constructor than `cls` when the
        annotation allows for it.

        Args:
            annotation:
                The type annotation to resolve.

        Returns:
            The resolved constructor, as the generator's return value.

        Raises:
            UnsupportedAnnotationError:
                `annotation` cannot be handled.
        """
        yield from ()  # Makes this function a generator, as overrides are
        raise UnsupportedAnnotationError(cls, annotation)

    @classmethod
    @abstractmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        """
        Decides whether this constructor applies to an annotation.

        Returns `True` only if this constructor unambiguously applies to `annotation`; if another
        constructor could handle it just as well, it must not be claimed here. A mere check that
        `resolve` would succeed is therefore not sufficient.

        Args:
            annotation:
                The type annotation to inspect.

        Returns:
            `True` if this constructor should be used for the annotation.
        """
        raise NotImplementedError(
            f"Expected `{cls.__name__}` to override `can_handle`; got the default implementation"
        )

    def __init__(
        self, constructor: Callable[A, R], *, repeatable: bool = False, count: int = 1
    ) -> None:
        """
        Args:
            constructor:
                Function that converts string values into a final value.
            repeatable:
                If `False`, options that use this constructor are given once. If `True`, they can
                be given multiple times: raw tokens are accumulated into a list and passed to the
                constructor as a single finalizer call after parsing completes. If `count` is
                greater than 1, each occurrence contributes a tuple of strings to the list rather
                than a plain string.
            count:
                How many CLI values are needed to construct a final value. For `repeatable`
                constructors, this corresponds to a single occurrence.

                A value of 0 means the constructor expects to be called without any arguments.
        """
        self._constructor = constructor
        self._repeatable = repeatable
        self._count = count

    @property
    def repeatable(self) -> bool:
        """Whether options that use this constructor default to being repeatable."""
        return self._repeatable

    @property
    def count(self) -> int:
        """
        Number of CLI values consumed to construct a value.

        For repeatable constructors, this is the number of CLI values per item.
        """
        return self._count

    def __call__(self, *args: A.args, **kwargs: A.kwargs) -> R:
        """
        Constructs the final value by calling the wrapped constructor.

        Args:
            *args:
                The positional arguments of the wrapped constructor.
            **kwargs:
                The keyword arguments of the wrapped constructor.

        Returns:
            The constructed value.
        """
        return self._constructor(*args, **kwargs)

    def __str__(self) -> str:
        """
        Describes this constructor as the type label shown for an option in help output.

        Composite constructors build theirs from their nested constructors' (e.g. `list[int]`), so
        the help describes the whole tree without special cases.

        Returns:
            The label, which defaults to the class name.
        """
        return type(self).__name__
