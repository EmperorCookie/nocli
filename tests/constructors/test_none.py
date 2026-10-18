from types import NoneType

import pytest

import nocli


class TestNone:
    def test_empty(self):
        assert nocli.constructors.NoneConstructor()("") is None

    def test_other(self):
        with pytest.raises(ValueError):
            nocli.constructors.NoneConstructor()("x")

    def test_not_falsy(self):
        with pytest.raises(ValueError):
            nocli.constructors.NoneConstructor(falsyIsNone=False)("")

    def test_values(self):
        parse = nocli.constructors.NoneConstructor(noneValues=("null", "nil"))
        assert (parse("null"), parse("nil")) == (None, None)

    def test_values_case_sensitive(self):
        with pytest.raises(ValueError):
            nocli.constructors.NoneConstructor(noneValues=("null",))("NULL")

    def test_values_case_insensitive(self):
        parse = nocli.constructors.NoneConstructor(noneValues=("null",), caseSensitive=False)
        assert parse("NULL") is None

    @pytest.mark.parametrize("annotation", [None, NoneType])
    def test_claims(self, annotation):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            annotation, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert isinstance(resolved, nocli.constructors.NoneConstructor)

    @pytest.mark.parametrize("annotation", [int, str, bool])
    def test_declines(self, annotation):
        assert not nocli.constructors.NoneConstructor.can_handle(annotation)

    def test_str(self):
        assert str(nocli.constructors.NoneConstructor()) == "None"
