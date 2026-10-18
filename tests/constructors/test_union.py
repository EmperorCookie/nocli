import typing

import pytest

import nocli


class TestUnion:
    def test_first(self):
        assert nocli.constructors.UnionConstructor(int, str)("5") == 5

    def test_next(self):
        assert nocli.constructors.UnionConstructor(int, str)("x") == "x"

    def test_declared_order(self):
        assert nocli.constructors.UnionConstructor(str, int)("5") == "5"

    def test_none_fail(self):
        with pytest.raises(nocli.exceptions.UnionConstructionError) as e:
            nocli.constructors.UnionConstructor(int, float)("x")
        assert e.value.value == "x"
        assert [str(c) for c, _ in e.value.failures] == ["int", "float"]
        assert all(isinstance(error, ValueError) for _, error in e.value.failures)

    def test_is_value_error(self):
        with pytest.raises(ValueError):
            nocli.constructors.UnionConstructor(int, float)("x")

    def test_empty(self):
        with pytest.raises(ValueError):
            nocli.constructors.UnionConstructor()

    def test_shape(self):
        parse = nocli.constructors.UnionConstructor(
            nocli.constructors.TupleConstructor(int, int),
            nocli.constructors.TupleConstructor(str, str),
        )
        assert (parse.count, parse.repeatable) == (2, False)

    def test_shape_mismatch(self):
        many = nocli.constructors.IterableConstructor(int)
        with pytest.raises(nocli.exceptions.ConstructorShapeError) as e:
            nocli.constructors.UnionConstructor(int, many)
        assert many in e.value.constructors

    def test_pair_mismatch(self):
        with pytest.raises(nocli.exceptions.ConstructorShapeError):
            nocli.constructors.UnionConstructor(int, nocli.constructors.TupleConstructor(int, int))

    def test_consumes_nothing(self):
        with pytest.warns(UserWarning):
            parse = nocli.constructors.UnionConstructor(
                nocli.constructors.FlagConstructor(1), nocli.constructors.FlagConstructor(2)
            )
        assert parse.count == 0
        parser = nocli.Parser().add_option("v", flags=["--v"], count=0, constructor=parse)
        assert parser.parse(["--v"])[1] == {"v": 1}

    def test_consumes_nothing_fallback(self):
        def fail():
            raise ValueError("boom")

        with pytest.warns(UserWarning):
            parse = nocli.constructors.UnionConstructor(
                nocli.constructors.CallableConstructor(fail, count=0),
                nocli.constructors.FlagConstructor(2),
            )
        parser = nocli.Parser().add_option("v", flags=["--v"], count=0, constructor=parse)
        assert parser.parse(["--v"])[1] == {"v": 2}

    def test_consumes_nothing_repeatable(self, recwarn):
        many = nocli.constructors.IterableConstructor(nocli.constructors.FlagConstructor(), list)
        parse = nocli.constructors.UnionConstructor(many, many)
        assert not recwarn.list
        assert parse([()]) == [True]

    def test_str(self):
        assert str(nocli.constructors.UnionConstructor(int, str)) == "int | str"

    @pytest.mark.parametrize(
        "annotation",
        [
            int | str,
            typing.Union[int, str],  # noqa: UP007 # Deprecated but must still work
            None | int,
        ],
    )
    def test_claims(self, annotation):
        assert nocli.constructors.UnionConstructor.can_handle(annotation)

    @pytest.mark.parametrize("annotation", [int, list[int], typing.Literal["a"]])
    def test_declines(self, annotation):
        assert not nocli.constructors.UnionConstructor.can_handle(annotation)

    @pytest.mark.parametrize(
        ("annotation", "value", "expected"),
        [
            (int | str, "5", 5),
            (int | str, "x", "x"),
            (str | int, "5", "5"),
            (typing.Union[int, str], "5", 5),  # noqa: UP007 # Deprecated but must still work
            (int | float, "1.5", 1.5),
            (int | typing.Literal["auto"], "auto", "auto"),
            (int | typing.Literal["auto"], "7", 7),
            (None | int, "", None),
            (None | int, "5", 5),
            (int | None | str, "x", "x"),
        ],
    )
    def test_resolve(self, annotation, value, expected):
        parse = nocli.constructors.ConstructorAbc.from_annotation(
            annotation, *nocli.DEFAULT_CONSTRUCTORS
        )
        result = parse(value)
        assert result == expected
        assert type(result) is type(expected)

    @pytest.mark.parametrize(
        "annotation",
        [
            int | None,
            typing.Optional[int],  # noqa: UP045 # Deprecated but must still work
        ],
    )
    def test_trailing_none(self, annotation):
        parse = nocli.constructors.ConstructorAbc.from_annotation(
            annotation, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert parse("5") == 5
        with pytest.raises(ValueError):
            parse("")

    def test_no_match(self):
        parse = nocli.constructors.ConstructorAbc.from_annotation(
            int | float, *nocli.DEFAULT_CONSTRUCTORS
        )
        with pytest.raises(ValueError):
            parse("x")

    def test_nested(self):
        parse = nocli.constructors.ConstructorAbc.from_annotation(
            list[int | typing.Literal["all"]], *nocli.DEFAULT_CONSTRUCTORS
        )
        assert parse(["1", "all"]) == [1, "all"]

    def test_unhandled_member(self):
        with pytest.raises(nocli.exceptions.NoConstructorError) as e:
            nocli.constructors.ConstructorAbc.from_annotation(
                int | str, nocli.constructors.UnionConstructor
            )
        assert e.value.annotation is int


class TestCollector:
    def test_records(self):
        collector = nocli.exceptions.UnionConstructionError.collector("v")
        member = nocli.constructors.CallableConstructor(int)
        with collector.context(member):
            member("x")
        with pytest.raises(nocli.exceptions.UnionConstructionError) as e:
            collector.raise_any()
        assert e.value.value == "v"
        assert [c for c, _ in e.value.failures] == [member]
        assert isinstance(e.value.failures[0][1], ValueError)

    def test_nothing_recorded(self):
        collector = nocli.exceptions.UnionConstructionError.collector("v")
        with collector.context(nocli.constructors.CallableConstructor(int)):
            pass
        collector.raise_any()

    def test_fresh(self):
        nocli.exceptions.UnionConstructionError.collector("v").raise_any()

    def test_in_order(self):
        collector = nocli.exceptions.UnionConstructionError.collector("v")
        ints = nocli.constructors.CallableConstructor(int)
        floats = nocli.constructors.CallableConstructor(float)
        for member in (ints, floats):
            with collector.context(member):
                member("x")
        with pytest.raises(nocli.exceptions.UnionConstructionError) as e:
            collector.raise_any()
        assert [c for c, _ in e.value.failures] == [ints, floats]

    def test_only_exceptions(self):
        collector = nocli.exceptions.UnionConstructionError.collector("v")
        with pytest.raises(KeyboardInterrupt):  # noqa: SIM117 # The `with` statement is the test subject
            with collector.context(nocli.constructors.CallableConstructor(int)):
                raise KeyboardInterrupt
