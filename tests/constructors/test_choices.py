import enum
import typing

import pytest

import nocli


class Color(enum.Enum):
    RED = 1
    GREEN = 2


class TestChoices:
    def test_valid(self):
        assert nocli.constructors.ChoicesConstructor("red", "green")("red") == "red"

    def test_invalid(self):
        with pytest.raises(ValueError):
            nocli.constructors.ChoicesConstructor("red", "green")("blue")

    def test_case_insensitive(self):
        parse = nocli.constructors.ChoicesConstructor("red", "green", caseSensitive=False)
        assert parse("RED") == "red"

    def test_case_sensitive(self):
        with pytest.raises(ValueError):
            nocli.constructors.ChoicesConstructor("red", caseSensitive=True)("RED")

    def test_finalizer(self):
        assert nocli.constructors.ChoicesConstructor("1", "2", finalizer=int)("2") == 2

    def test_literal(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            typing.Literal["a", "b"], *nocli.DEFAULT_CONSTRUCTORS
        )
        assert (resolved("a"), resolved("b")) == ("a", "b")
        with pytest.raises(ValueError):
            resolved("c")

    @pytest.mark.parametrize("annotation", [typing.Literal["a"], Color])
    def test_claims(self, annotation):
        assert nocli.constructors.ChoicesConstructor.can_handle(annotation)

    @pytest.mark.parametrize("annotation", [str, int, list[str], typing.Optional[str]])  # noqa: UP045 # Deprecated but must still work
    def test_declines(self, annotation):
        assert not nocli.constructors.ChoicesConstructor.can_handle(annotation)

    @pytest.mark.parametrize(
        ("choices", "display"),
        [
            (("a", "b"), "'a' | 'b'"),
            (("b", "a"), "'b' | 'a'"),
            (("a",), "'a'"),
            (("a", "b", "a"), "'a' | 'b'"),
        ],
    )
    def test_str(self, choices, display):
        assert str(nocli.constructors.ChoicesConstructor(*choices)) == display

    def test_str_insensitive(self):
        parse = nocli.constructors.ChoicesConstructor("a", "b", caseSensitive=False)
        assert str(parse) == "choices<ins>['a' | 'b']"


class TestEnum:
    def test_valid(self):
        assert nocli.constructors.ChoicesConstructor.from_enum(Color)("RED") == Color.RED

    def test_case_insensitive(self):
        parse = nocli.constructors.ChoicesConstructor.from_enum(Color, caseSensitive=False)
        assert parse("red") == Color.RED

    def test_invalid(self):
        with pytest.raises(ValueError):
            nocli.constructors.ChoicesConstructor.from_enum(Color)("BLUE")

    def test_case_sensitive(self):
        with pytest.raises(ValueError):
            nocli.constructors.ChoicesConstructor.from_enum(Color, caseSensitive=True)("red")

    def test_resolve(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            Color, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert resolved("GREEN") == Color.GREEN
