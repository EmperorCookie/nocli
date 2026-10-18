from collections import abc
from collections.abc import Callable, Collection, Generator, Iterable, Mapping
from typing import Any, ClassVar, Generic, TypeVar, get_args, get_origin

from .._compat import Self
from ..exceptions import IterableElementShapeError, UnsupportedAnnotationError
from ._base import ConstructorAbc, Raw
from ._callable import CallableConstructor
from ._tuple import TupleConstructor

# Python < 3.12 (would use variadic generics otherwise)
N = TypeVar("N")  # What each nested value is constructed into
R = TypeVar("R", bound=Collection[Any])  # What the nested values are finalized into
K = TypeVar("K")  # What the key of a mapping is constructed into
V = TypeVar("V")  # What the value of a mapping is constructed into
M = TypeVar("M", bound=Mapping[Any, Any])  # What the pairs of a mapping are finalized into


def _tuple(items: Iterable[N]) -> tuple[N, ...]:
    """
    Builds a tuple of the items, typed by their element type.

    The type checker infers the result of a default argument from its own type, and the builtin
    `tuple` has no element type to give; this one does.
    """
    return tuple(items)


def _dict(items: Iterable[tuple[K, V]]) -> dict[K, V]:
    """
    Builds a dict of the pairs, typed by their key and value types.

    The type checker infers the result of a default argument from its own type, and the builtin
    `dict` has no key and value types to give; this one does.
    """
    return dict(items)


class IterableConstructor(ConstructorAbc[[Iterable[Raw]], R], Generic[N, R]):
    """
    Constructs any value from an iterable of values, each of which is constructed by a nested
    constructor. The option it is used for is repeatable by default.

    Handles `list`, `set`, `frozenset`, `dict` and `tuple[X, ...]` annotations, along with the
    abstract collections from `collections.abc` and `typing` (e.g. `Sequence`, `Mapping`). The
    abstract ones resolve to the strictest builtin that satisfies them: read-only abstractions get
    immutable types (`Sequence` is a `tuple`, `Set` a `frozenset`), and mutable ones get mutable
    types. Subclasses of those are not claimed, since they may construct differently.

    A nested constructor given as a plain callable is used as it is: the constructors that `Cli`
    uses for type hints don't apply to it, so `bool` is the builtin `bool`, not a
    `BoolConstructor`. To have them apply, derive the nested constructor with
    `ConstructorAbc.from_annotation`.
    """

    # Annotation origins and the callable that finalizes each; abstract collections get the
    # strictest builtin that satisfies the collection. There is no immutable builtin mapping, so
    # mappings are a `dict`. The typed stand-ins for `tuple` and `dict` are entries too, to display
    # as the builtins being stood in for
    _FINALIZERS: ClassVar[dict[Callable[..., Any], Callable[[Iterable[Any]], Any]]] = {
        list: list,
        set: set,
        frozenset: frozenset,
        dict: dict,
        tuple: tuple,
        abc.Sequence: tuple,
        abc.MutableSequence: list,
        abc.Collection: tuple,
        abc.Iterable: tuple,
        abc.Set: frozenset,
        abc.MutableSet: set,
        abc.Mapping: dict,
        abc.MutableMapping: dict,
        _tuple: tuple,
        _dict: dict,
    }
    _MAPPINGS: ClassVar[tuple[type, ...]] = (dict, abc.Mapping, abc.MutableMapping)

    @classmethod
    def resolve(
        cls: type[Self], annotation: Any
    ) -> Generator[Any, ConstructorAbc[..., Any], ConstructorAbc[..., Any]]:
        if not cls.can_handle(annotation):
            raise UnsupportedAnnotationError(cls, annotation)
        origin = get_origin(annotation) or annotation
        args = get_args(annotation)
        if origin in cls._MAPPINGS:
            key, value = args or (str, str)
            return cls.from_mapping((yield key), (yield value), cls._FINALIZERS[origin])
        nested = yield args[0] if args else str
        return cls(nested, cls._FINALIZERS[origin])

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        origin = get_origin(annotation) or annotation
        # Only exact matches; a subclass may construct differently (e.g. `NamedTuple`)
        if not isinstance(origin, type) or origin not in cls._FINALIZERS:
            return False
        if origin is tuple:
            # Fixed length tuples are for the tuple constructor to handle
            return not get_args(annotation) or ... in get_args(annotation)
        return True

    @classmethod
    def from_mapping(
        cls: "type[IterableConstructor[Any, Any]]",
        key: Callable[..., K],
        value: Callable[..., V],
        finalizer: Callable[[Iterable[tuple[K, V]]], M] = _dict,
        *,
        minItems: int | None = None,
        maxItems: int | None = None,
    ) -> "IterableConstructor[tuple[K, V], M]":
        """
        Builds a constructor for a mapping, from repeated pairs of a key and a value.

        The same as passing a `TupleConstructor` of the two to the constructor, except that the key
        and value types are carried through to the type checker.

        Args:
            key:
                The constructor to use for the key of each pair.
            value:
                The constructor to use for the value of each pair.
            finalizer:
                The constructor to use for the entire mapping, which is given the pairs.
            minItems:
                The minimum number of pairs that must be present.
            maxItems:
                The maximum number of pairs that may be present.

        Returns:
            The constructor, which consumes as many CLI values per pair as `key` and `value` do in
            total.
        """
        pair = TupleConstructor[tuple[K, V]](key, value)
        return cls(pair, finalizer, minItems=minItems, maxItems=maxItems)

    def __init__(
        self,
        nested: Callable[..., N],
        finalizer: Callable[[Iterable[N]], R] = _tuple,
        *,
        minItems: int | None = None,
        maxItems: int | None = None,
    ) -> None:
        """
        Args:
            nested:
                The constructor to use for individual elements of the iterable. The number of CLI
                values it consumes is the number consumed by each repetition of this constructor.
                If that is none, it is called without arguments once per repetition.
            finalizer:
                The constructor to use for the entire iterable.
            minItems:
                The minimum number of elements that must be present in the iterable.
            maxItems:
                The maximum number of elements that may be present in the iterable.

        Raises:
            IterableElementShapeError:
                `nested` is repeatable; repetitions can't be nested.
        """
        nested = CallableConstructor.coerce(nested)
        if nested.repeatable:
            raise IterableElementShapeError(nested)
        super().__init__(self._construct, repeatable=True, count=nested.count)
        self._nested = nested
        self._finalizer = finalizer
        self._minItems = minItems
        self._maxItems = maxItems

    def _construct(self, values: Iterable[Raw]) -> R:
        """
        Constructs each value with the nested constructor, then finalizes and validates them.

        Raises:
            ValueError:
                There are fewer than `minItems` or more than `maxItems` items.
        """
        if self._nested.count == 0:
            # Each occurrence is empty, as the nested constructor consumes no values
            result = self._finalizer(self._nested() for _ in values)
        else:
            result = self._finalizer(self._nested(v) for v in values)
        if self._minItems is not None and len(result) < self._minItems:
            raise ValueError(f"Expected at least {self._minItems} items; got {len(result)}")
        if self._maxItems is not None and len(result) > self._maxItems:
            raise ValueError(f"Expected at most {self._maxItems} items; got {len(result)}")
        return result

    def __str__(self) -> str:
        finalizer = self._FINALIZERS.get(self._finalizer, self._finalizer)
        # A tuple is of a fixed length unless said otherwise, as in Python's `tuple[int, ...]`
        variadic = ", ..." if finalizer is tuple else ""
        return f"{getattr(finalizer, '__name__', 'array')}[{self._nested}{variadic}]"
