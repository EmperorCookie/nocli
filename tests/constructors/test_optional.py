import pytest

import nocli


class TestOptional:
    def test_value(self):
        assert nocli.constructors.OptionalConstructor(int)("42") == 42

    def test_empty(self):
        assert nocli.constructors.OptionalConstructor(int)("") is None

    def test_str_passthrough(self):
        assert nocli.constructors.OptionalConstructor(str)("hello") == "hello"

    def test_str_empty(self):
        assert nocli.constructors.OptionalConstructor(str)("") is None

    def test_values(self):
        parse = nocli.constructors.OptionalConstructor(int, noneValues=("null",))
        assert parse("null") is None

    def test_not_falsy(self):
        with pytest.raises(ValueError):
            nocli.constructors.OptionalConstructor(int, falsyIsNone=False)("")

    def test_invalid(self):
        with pytest.raises(ValueError):
            nocli.constructors.OptionalConstructor(int)("x")

    def test_never_selected(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            int | None, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert not isinstance(resolved, nocli.constructors.OptionalConstructor)

    def test_declines(self):
        assert not nocli.constructors.OptionalConstructor.can_handle(int | None)

    def test_str(self):
        assert str(nocli.constructors.OptionalConstructor(int)) == "None | int"
