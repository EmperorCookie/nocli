import collections
import typing
from collections import abc

import pytest

import nocli


class Point(typing.NamedTuple):
    x: int
    y: int


class TestIterable:
    def test_default_finalizer(self):
        assert nocli.constructors.IterableConstructor(int)(["1", "2"]) == (1, 2)

    def test_finalizer(self):
        assert nocli.constructors.IterableConstructor(int, list)(["1", "2"]) == [1, 2]
        assert nocli.constructors.IterableConstructor(int, set)(["1", "1"]) == {1}

    def test_nested_flag(self):
        parse = nocli.constructors.IterableConstructor(nocli.constructors.FlagConstructor(), list)
        assert (parse.count, parse.repeatable) == (0, True)
        assert parse([(), (), ()]) == [True, True, True]

    def test_nested_tuple(self):
        nested = nocli.constructors.TupleConstructor(str, int)
        assert nocli.constructors.IterableConstructor(nested, dict)([("a", "1")]) == {"a": 1}

    def test_empty(self):
        assert nocli.constructors.IterableConstructor(int, list)([]) == []

    def test_mapping(self):
        parse = nocli.constructors.IterableConstructor.from_mapping(str, int)
        assert parse([("a", "1"), ("b", "2")]) == {"a": 1, "b": 2}

    def test_mapping_shape(self):
        parse = nocli.constructors.IterableConstructor.from_mapping(str, int)
        assert (parse.count, parse.repeatable) == (2, True)

    def test_mapping_nested_value(self):
        pair = nocli.constructors.TupleConstructor(int, int)
        parse = nocli.constructors.IterableConstructor.from_mapping(str, pair)
        assert parse.count == 3
        assert parse([("a", "1", "2")]) == {"a": (1, 2)}

    def test_mapping_limits(self):
        parse = nocli.constructors.IterableConstructor.from_mapping(str, int, maxItems=1)
        with pytest.raises(ValueError):
            parse([("a", "1"), ("b", "2")])

    def test_mapping_finalizer(self):
        parse = nocli.constructors.IterableConstructor.from_mapping(
            str, int, collections.OrderedDict
        )
        assert type(parse([("a", "1")])) is collections.OrderedDict

    def test_mapping_table(self):
        class Ordered(nocli.constructors.IterableConstructor):
            _FINALIZERS: typing.ClassVar = {
                **nocli.constructors.IterableConstructor._FINALIZERS,
                abc.Mapping: collections.OrderedDict,
            }

        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            abc.Mapping[str, int], Ordered, nocli.constructors.CallableConstructor
        )
        assert type(resolved([("a", "1")])) is collections.OrderedDict

    def test_mapping_bad_value(self):
        parse = nocli.constructors.IterableConstructor.from_mapping(str, int)
        with pytest.raises(ValueError):
            parse([("a", "x")])

    def test_min(self):
        parse = nocli.constructors.IterableConstructor(int, list, minItems=2)
        assert parse(["1", "2"]) == [1, 2]
        with pytest.raises(ValueError):
            parse(["1"])

    def test_max(self):
        parse = nocli.constructors.IterableConstructor(int, list, maxItems=1)
        assert parse(["1"]) == [1]
        with pytest.raises(ValueError):
            parse(["1", "2"])

    def test_shape(self):
        parse = nocli.constructors.IterableConstructor(int)
        assert (parse.count, parse.repeatable) == (1, True)

    def test_shape_nested(self):
        parse = nocli.constructors.IterableConstructor(
            nocli.constructors.TupleConstructor(int, int)
        )
        assert (parse.count, parse.repeatable) == (2, True)

    def test_nested_repeatable(self):
        inner = nocli.constructors.IterableConstructor(int)
        with pytest.raises(nocli.exceptions.ConstructorShapeError) as e:
            nocli.constructors.IterableConstructor(inner)
        assert inner in e.value.constructors

    def test_bad_element(self):
        with pytest.raises(ValueError):
            nocli.constructors.IterableConstructor(int)(["x"])

    @pytest.mark.parametrize(
        "annotation",
        [
            list,
            list[int],
            set[int],
            frozenset[int],
            dict[str, int],
            dict,
            tuple,
            tuple[int, ...],
            typing.List[int],  # noqa: UP006 # Deprecated but must still work
            typing.Dict[str, int],  # noqa: UP006 # Deprecated but must still work
            abc.Sequence[int],
            abc.Mapping[str, int],
            abc.MutableMapping[str, int],
            abc.Set[int],
            abc.MutableSet[int],
            typing.Iterable[int],
        ],
    )
    def test_claims(self, annotation):
        assert nocli.constructors.IterableConstructor.can_handle(annotation)

    @pytest.mark.parametrize(
        "annotation",
        [
            tuple[int, str],
            int,
            str,
            Point,
            typing.Deque[int],  # noqa: UP006 # Deprecated but must still work
            typing.DefaultDict,  # noqa: UP006 # Deprecated but must still work
        ],
    )
    def test_declines(self, annotation):
        assert not nocli.constructors.IterableConstructor.can_handle(annotation)

    @pytest.mark.parametrize(
        ("annotation", "values", "expected"),
        [
            (list[int], ["1", "2"], [1, 2]),
            (typing.List[int], ["1"], [1]),  # noqa: UP006 # Deprecated but must still work
            (set[int], ["1", "1"], {1}),
            (frozenset[int], ["1"], frozenset({1})),
            (tuple[int, ...], ["1", "2"], (1, 2)),
            (list, ["a"], ["a"]),
            (abc.Sequence[int], ["1"], (1,)),
            (abc.MutableSequence[int], ["1"], [1]),
            (abc.Collection[int], ["1"], (1,)),
            (abc.Iterable[int], ["1"], (1,)),
            (abc.Set[int], ["1"], frozenset({1})),
            (abc.MutableSet[int], ["1"], {1}),
            (dict[str, int], [("a", "1")], {"a": 1}),
            (abc.Mapping[str, int], [("a", "1")], {"a": 1}),
            (abc.MutableMapping[str, tuple[int, int]], [("a", "1", "2")], {"a": (1, 2)}),
        ],
    )
    def test_resolve(self, annotation, values, expected):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            annotation, *nocli.DEFAULT_CONSTRUCTORS
        )
        result = resolved(values)
        assert result == expected
        assert type(result) is type(expected)

    def test_subclass_unclaimed(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            Point, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert not isinstance(resolved, nocli.constructors.IterableConstructor)

    @pytest.mark.parametrize(
        ("constructor", "display"),
        [
            (nocli.constructors.IterableConstructor(int, list), "list[int]"),
            (nocli.constructors.IterableConstructor(int), "tuple[int, ...]"),
            (
                nocli.constructors.IterableConstructor(
                    nocli.constructors.TupleConstructor(int, int)
                ),
                "tuple[(int, int), ...]",
            ),
            (nocli.constructors.IterableConstructor(int, set), "set[int]"),
            (
                nocli.constructors.IterableConstructor(
                    nocli.constructors.TupleConstructor(str, int), dict
                ),
                "dict[(str, int)]",
            ),
            (nocli.constructors.IterableConstructor.from_mapping(str, int), "dict[(str, int)]"),
        ],
    )
    def test_str(self, constructor, display):
        assert str(constructor) == display
