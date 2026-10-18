import pytest

import nocli


class TestFlag:
    def test_present(self):
        assert nocli.constructors.FlagConstructor()() is True

    def test_present_value(self):
        assert nocli.constructors.FlagConstructor(False)() is False
        assert nocli.constructors.FlagConstructor(9001)() == 9001

    def test_consumes_nothing(self):
        parse = nocli.constructors.FlagConstructor()
        assert (parse.count, parse.repeatable) == (0, False)

    @pytest.mark.parametrize("annotation", [bool, int, None])
    def test_declines(self, annotation):
        assert not nocli.constructors.FlagConstructor.can_handle(annotation)

    def test_bool_stays_bool(self):
        resolved = nocli.constructors.ConstructorAbc.from_annotation(
            bool, *nocli.DEFAULT_CONSTRUCTORS
        )
        assert not isinstance(resolved, nocli.constructors.FlagConstructor)

    def test_str(self):
        assert str(nocli.constructors.FlagConstructor()) == "flag"
