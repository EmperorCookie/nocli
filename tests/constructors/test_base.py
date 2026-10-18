import enum
import typing

import pytest

import nocli


class Color(enum.Enum):
    RED = 1
    GREEN = 2


def claims(target, tag):
    """A constructor class that claims exactly `target` and tags what it constructs."""

    class Claim(nocli.constructors.ConstructorAbc):
        @classmethod
        def can_handle(cls, annotation):
            return annotation is target

        @classmethod
        def resolve(cls, annotation):
            yield from ()
            return cls(lambda value: (tag, value))

    return Claim


class TestAbc:
    def test_abstract(self):
        with pytest.raises(TypeError):
            nocli.constructors.ConstructorAbc(str)  # pyright: ignore[reportAbstractUsage]

    def test_resolve_default(self):
        class Bare(nocli.constructors.ConstructorAbc):
            @classmethod
            def can_handle(cls, annotation):
                return False

        with pytest.raises(nocli.exceptions.UnsupportedAnnotationError) as e:
            next(Bare.resolve(int))
        assert e.value.constructor is Bare
        assert e.value.annotation is int

    def test_shape_default(self):
        class Bare(nocli.constructors.ConstructorAbc):
            @classmethod
            def can_handle(cls, annotation):
                return False

        assert (Bare(str).count, Bare(str).repeatable) == (1, False)


class TestCallable:
    def test_call(self):
        assert nocli.constructors.CallableConstructor(int)("4") == 4

    @pytest.mark.parametrize("annotation", [int, len, str, lambda v: v])
    def test_handles(self, annotation):
        assert nocli.constructors.CallableConstructor.can_handle(annotation)

    @pytest.mark.parametrize(
        "annotation",
        [
            list[int],
            typing.Optional[int],  # noqa: UP045 # Deprecated but must still work
            42,
            None,
        ],
    )
    def test_declines(self, annotation):
        assert not nocli.constructors.CallableConstructor.can_handle(annotation)

    def test_resolve(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            int, nocli.constructors.CallableConstructor
        )
        assert isinstance(resolved, nocli.constructors.CallableConstructor)
        assert resolved("5") == 5

    def test_shape(self):
        parse = nocli.constructors.CallableConstructor(tuple, count=2, repeatable=True)
        assert (parse.count, parse.repeatable) == (2, True)

    def test_str(self):
        assert str(nocli.constructors.CallableConstructor(len)) == "len"

    def test_str_lambda(self):
        assert str(nocli.constructors.CallableConstructor(lambda v: v)) == "<lambda>"

    def test_str_override(self):
        assert str(nocli.constructors.CallableConstructor(len, displayType="size")) == "size"


class TestFromAnnotation:
    def test_first_wins(self):
        a, b = claims(int, "a"), claims(int, "b")
        assert nocli.constructors.ConstructorAbc.from_annotation(int, a, b)("1") == ("a", "1")
        assert nocli.constructors.ConstructorAbc.from_annotation(int, b, a)("1") == ("b", "1")

    def test_nested(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            list[int], claims(int, "n"), *nocli.DEFAULT_CONSTRUCTORS
        )
        assert resolved(["1", "2"]) == [("n", "1"), ("n", "2")]

    def test_only_given(self):
        with pytest.raises(nocli.exceptions.NoConstructorError) as e:
            nocli.constructors.ConstructorAbc.from_annotation(int)
        assert e.value.annotation is int

    def test_unhandled_nested(self):
        with pytest.raises(nocli.exceptions.NoConstructorError) as e:
            nocli.constructors.ConstructorAbc.from_annotation(list[3], *nocli.DEFAULT_CONSTRUCTORS)
        assert e.value.annotation == 3

    def test_inherited(self):
        resolved = nocli.constructors.TupleConstructor.from_annotation(
            int, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert resolved("3") == 3

    def test_subclass_unclaimed(self):
        class Point(typing.NamedTuple):
            x: int
            y: int

        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            Point, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert isinstance(resolved, nocli.constructors.CallableConstructor)


# annotation, display, count, repeatable
SHAPES = [
    (int, "int", 1, False),
    (bool, "bool", 1, False),
    (list, "list[str]", 1, True),
    (tuple, "tuple[str, ...]", 1, True),
    (list[int], "list[int]", 1, True),
    (set[str], "set[str]", 1, True),
    (frozenset[int], "frozenset[int]", 1, True),
    (tuple[int, ...], "tuple[int, ...]", 1, True),
    (typing.Sequence[str], "tuple[str, ...]", 1, True),
    (tuple[int, str], "(int, str)", 2, False),
    (tuple[int, tuple[int, int]], "(int, (int, int))", 3, False),
    (dict, "dict[(str, str)]", 2, True),
    (dict[str, int], "dict[(str, int)]", 2, True),
    (typing.Mapping[str, int], "dict[(str, int)]", 2, True),
    (list[tuple[int, int]], "list[(int, int)]", 2, True),
    (typing.Literal["a", "b"], "'a' | 'b'", 1, False),
    (typing.Literal["a"], "'a'", 1, False),
    (Color, "'RED' | 'GREEN'", 1, False),
    (int | str, "int | str", 1, False),
    (typing.Union[int, str], "int | str", 1, False),  # noqa: UP007 # Deprecated but must still work
    (None | int, "None | int", 1, False),
    (int | None, "int", 1, False),
    (typing.Optional[int], "int", 1, False),  # noqa: UP045 # Deprecated but must still work
    (int | None | str, "int | str", 1, False),
    (list[int | typing.Literal["all"]], "list[int | 'all']", 1, True),
]


@pytest.mark.parametrize(("annotation", "display", "count", "repeatable"), SHAPES)
def test_defaults(annotation, display, count, repeatable):
    resolved = nocli.constructors.ConstructorAbc.from_annotation(
        annotation, *nocli.DEFAULT_CONSTRUCTORS
    )
    assert str(resolved) == display
    assert (resolved.count, resolved.repeatable) == (count, repeatable)
