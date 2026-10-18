import pytest

import nocli


class TestLiteral:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [("42", 42), ("[1, 2, 3]", [1, 2, 3]), ("{'a': 1}", {"a": 1}), ("None", None)],
    )
    def test_value(self, text, expected):
        assert nocli.constructors.LiteralEvalConstructor()(text) == expected

    def test_bool(self):
        assert nocli.constructors.LiteralEvalConstructor()("True") is True

    def test_invalid(self):
        with pytest.raises((ValueError, SyntaxError)):
            nocli.constructors.LiteralEvalConstructor()("not a literal")

    def test_declines(self):
        assert not nocli.constructors.LiteralEvalConstructor.can_handle(object)


class TestPlusLiteral:
    def test_plain(self):
        assert nocli.constructors.LiteralEvalConstructor(plus=True)("hello") == "hello"

    def test_plus(self):
        assert nocli.constructors.LiteralEvalConstructor(plus=True)("+42") == 42

    def test_plus_list(self):
        assert nocli.constructors.LiteralEvalConstructor(plus=True)("+[1, 2]") == [1, 2]

    def test_escaped_plus(self):
        assert nocli.constructors.LiteralEvalConstructor(plus=True)(r"\+hello") == "+hello"

    def test_escaped_backslash(self):
        assert nocli.constructors.LiteralEvalConstructor(plus=True)(r"\\hello") == r"\hello"

    def test_empty(self):
        assert nocli.constructors.LiteralEvalConstructor(plus=True)("") == ""
