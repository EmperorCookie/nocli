import pytest

import nocli


class TestTuple:
    def test_elements(self):
        assert nocli.constructors.TupleConstructor(int, str)(("1", "x")) == (1, "x")

    def test_plain_callables(self):
        assert nocli.constructors.TupleConstructor(int, float)(("1", "2.5")) == (1, 2.5)

    def test_count(self):
        assert nocli.constructors.TupleConstructor(int, str).count == 2

    def test_not_repeatable(self):
        assert not nocli.constructors.TupleConstructor(int, str).repeatable

    def test_nested(self):
        parse = nocli.constructors.TupleConstructor(
            int, nocli.constructors.TupleConstructor(int, int)
        )
        assert parse.count == 3
        assert parse(("1", "2", "3")) == (1, (2, 3))

    def test_flag_element(self):
        parse = nocli.constructors.TupleConstructor(int, nocli.constructors.FlagConstructor())
        assert parse.count == 1
        assert parse("5") == (5, True)

    def test_factory_element(self):
        parse = nocli.constructors.TupleConstructor(
            nocli.constructors.CallableConstructor(lambda: "key", count=0), int
        )
        assert parse.count == 1
        assert parse("5") == ("key", 5)

    def test_only_flags(self):
        parse = nocli.constructors.TupleConstructor(
            nocli.constructors.FlagConstructor(1), nocli.constructors.FlagConstructor(2)
        )
        assert parse.count == 0
        parser = nocli.Parser().add_option("v", flags=["--v"], count=0, constructor=parse)
        assert parser.parse(["--v"])[1] == {"v": (1, 2)}

    def test_repeatable_element(self):
        element = nocli.constructors.IterableConstructor(int)
        with pytest.raises(nocli.exceptions.ConstructorShapeError) as e:
            nocli.constructors.TupleConstructor(int, element)
        assert element in e.value.constructors

    def test_resolve(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            tuple[int, str], *nocli.DEFAULT_CONSTRUCTORS
        )
        assert isinstance(resolved, nocli.constructors.TupleConstructor)
        assert resolved(("1", "x")) == (1, "x")

    def test_resolve_nested(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            tuple[int, tuple[int, int]], *nocli.DEFAULT_CONSTRUCTORS
        )
        assert resolved(("1", "2", "3")) == (1, (2, 3))

    @pytest.mark.parametrize("annotation", [tuple[int, str], tuple[int], tuple[int, int, int]])
    def test_claims(self, annotation):
        assert nocli.constructors.TupleConstructor.can_handle(annotation)

    @pytest.mark.parametrize("annotation", [tuple[int, ...], tuple, list[int], int])
    def test_declines(self, annotation):
        assert not nocli.constructors.TupleConstructor.can_handle(annotation)

    def test_str(self):
        assert str(nocli.constructors.TupleConstructor(int, str)) == "(int, str)"
