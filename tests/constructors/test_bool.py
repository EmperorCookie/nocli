import pytest

import nocli


class TestBool:
    @pytest.mark.parametrize("value", ["yes", "true", "y", "t", "on"])
    def test_true(self, value):
        assert nocli.constructors.BoolConstructor()(value) is True

    @pytest.mark.parametrize("value", ["no", "false", "n", "f", "off"])
    def test_false(self, value):
        assert nocli.constructors.BoolConstructor()(value) is False

    def test_unknown(self):
        with pytest.raises(ValueError):
            nocli.constructors.BoolConstructor()("nope")

    def test_invalid(self):
        parse = nocli.constructors.BoolConstructor(invalidFinalizer=lambda _: False)
        assert parse("nope") is False

    def test_invalid_gets_value(self):
        parse = nocli.constructors.BoolConstructor(invalidFinalizer=lambda value: value.upper())
        assert parse("nope") == "NOPE"

    def test_finalizer(self):
        parse = nocli.constructors.BoolConstructor(finalizer=str)
        assert (parse("yes"), parse("no")) == ("True", "False")

    def test_case_insensitive(self):
        assert nocli.constructors.BoolConstructor()("YES") is True

    def test_case_sensitive_reject(self):
        with pytest.raises(ValueError):
            nocli.constructors.BoolConstructor(caseSensitive=True)("YES")

    def test_case_sensitive_accept(self):
        assert nocli.constructors.BoolConstructor(caseSensitive=True)("yes") is True

    @pytest.mark.parametrize(("value", "expected"), [("1", True), ("0", False), ("-1", False)])
    def test_numeric(self, value, expected):
        assert nocli.constructors.BoolConstructor()(value) is expected

    def test_float_predicate(self):
        parse = nocli.constructors.BoolConstructor(floatPredicate=lambda f: f >= 0.5)
        assert (parse("0.5"), parse("0.4")) == (True, False)

    def test_float_predicate_off(self):
        parse = nocli.constructors.BoolConstructor(
            floatPredicate=None, invalidFinalizer=lambda _: False
        )
        assert parse("1") is False

    def test_non_finite(self):
        with pytest.raises(ValueError):
            nocli.constructors.BoolConstructor()("nan")

    def test_true_options(self):
        parse = nocli.constructors.BoolConstructor(
            trueOptions=("on",), floatPredicate=None, invalidFinalizer=lambda _: False
        )
        assert (parse("on"), parse("yes")) == (True, False)

    def test_claims_bool(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            bool, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert isinstance(resolved, nocli.constructors.BoolConstructor)
        with pytest.raises(ValueError):
            resolved("maybe")

    @pytest.mark.parametrize("annotation", [int, str, None])
    def test_declines(self, annotation):
        assert not nocli.constructors.BoolConstructor.can_handle(annotation)

    def test_str(self):
        assert str(nocli.constructors.BoolConstructor()) == "bool"
