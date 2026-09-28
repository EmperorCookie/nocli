import pytest
from enum import Enum

from nocli.constructors import (
    BoolConstructor,
    HexStringConstructor,
    HexConstructor,
    IntOrHexConstructor,
    LiteralEvalConstructor,
    OptionalConstructor,
    ChoicesConstructor,
)


class TestBool:
    @pytest.mark.parametrize("value", ["yes", "true", "y", "t", "on"])
    def test_default_true_values(self, value):
        assert BoolConstructor()(value) is True

    @pytest.mark.parametrize("value", ["no", "false", "n", "f", "off"])
    def test_default_false_values(self, value):
        assert BoolConstructor()(value) is False

    def test_unknown_string_raises_by_default(self):
        with pytest.raises(ValueError):
            BoolConstructor()("nope")

    def test_invalid_false_resolves_unknown(self):
        assert BoolConstructor(invalid=False)("nope") is False

    def test_invalid_true_resolves_unknown(self):
        assert BoolConstructor(invalid=True)("nope") is True

    def test_case_insensitive_by_default(self):
        assert BoolConstructor()("YES") is True

    def test_case_sensitive_rejects_wrong_case(self):
        with pytest.raises(ValueError):
            BoolConstructor(caseSensitive=True)("YES")

    def test_case_sensitive_accepts_exact_match(self):
        assert BoolConstructor(caseSensitive=True)("yes") is True

    def test_numeric_positive_is_true(self):
        assert BoolConstructor()("1") is True

    def test_numeric_zero_is_false(self):
        assert BoolConstructor()("0") is False

    def test_numeric_negative_is_false(self):
        assert BoolConstructor()("-1") is False

    def test_custom_float_predicate(self):
        parse = BoolConstructor(floatPredicate=lambda f: f >= 0.5)
        assert parse("0.5") is True
        assert parse("0.4") is False

    def test_float_predicate_none_disables_numeric(self):
        parse = BoolConstructor(floatPredicate=None, invalid=False)
        assert parse("1") is False

    def test_non_finite_values_use_string_options(self):
        with pytest.raises(ValueError):
            BoolConstructor()("nan")

    def test_custom_true_options(self):
        parse = BoolConstructor(trueOptions=("on",), floatPredicate=None, invalid=False)
        assert parse("on") is True
        assert parse("yes") is False


class TestHexString:
    def test_0x_prefix_preserved(self):
        assert HexStringConstructor()("0xff") == "0xff"

    def test_hash_prefix_converted(self):
        assert HexStringConstructor()("#ff") == "0xff"

    def test_no_prefix_accepted(self):
        assert HexStringConstructor()("ff") == "0xff"

    def test_no_prefix_rejected(self):
        with pytest.raises(ValueError):
            HexStringConstructor(acceptNoPrefix=False)("ff")

    def test_convert_case_upper(self):
        assert HexStringConstructor(convertCase="upper")("0xab") == "0xAB"

    def test_convert_case_lower(self):
        assert HexStringConstructor(convertCase="lower")("0xAB") == "0xab"

    def test_invalid_hex_raises(self):
        with pytest.raises(ValueError):
            HexStringConstructor()("0xzz")

    def test_custom_output_prefix(self):
        assert HexStringConstructor(outputPrefix="#")("0xff") == "#ff"


class TestHex:
    def test_0x_prefix(self):
        assert HexConstructor()("0xff") == 255

    def test_hash_prefix(self):
        assert HexConstructor()("#ff") == 255

    def test_no_prefix_accepted(self):
        assert HexConstructor()("ff") == 255

    def test_no_prefix_rejected(self):
        with pytest.raises(ValueError):
            HexConstructor(acceptNoPrefix=False)("ff")


class TestIntOrHex:
    def test_decimal(self):
        assert IntOrHexConstructor()("255") == 255

    def test_0x_hex(self):
        assert IntOrHexConstructor()("0xff") == 255

    def test_hash_hex(self):
        assert IntOrHexConstructor()("#ff") == 255

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            IntOrHexConstructor()("abc")


class TestLiteral:
    def test_integer(self):
        assert LiteralEvalConstructor()("42") == 42

    def test_list(self):
        assert LiteralEvalConstructor()("[1, 2, 3]") == [1, 2, 3]

    def test_dict(self):
        assert LiteralEvalConstructor()("{'a': 1}") == {"a": 1}

    def test_bool(self):
        assert LiteralEvalConstructor()("True") is True

    def test_none(self):
        assert LiteralEvalConstructor()("None") is None

    def test_invalid_raises(self):
        with pytest.raises((ValueError, SyntaxError)):
            LiteralEvalConstructor()("not a literal")


class TestPlusLiteral:
    def test_plain_string(self):
        assert LiteralEvalConstructor(plus=True)("hello") == "hello"

    def test_plus_prefix_evaluates_literal(self):
        assert LiteralEvalConstructor(plus=True)("+42") == 42

    def test_plus_prefix_list(self):
        assert LiteralEvalConstructor(plus=True)("+[1, 2]") == [1, 2]

    def test_escaped_plus(self):
        assert LiteralEvalConstructor(plus=True)(r"\+hello") == "+hello"

    def test_escaped_backslash(self):
        assert LiteralEvalConstructor(plus=True)(r"\\hello") == r"\hello"

    def test_empty_string_passthrough(self):
        assert LiteralEvalConstructor(plus=True)("") == ""


class TestNullable:
    def test_non_empty_calls_constructor(self):
        assert OptionalConstructor(int)("42") == 42

    def test_empty_string_returns_none(self):
        assert OptionalConstructor(int)("") is None

    def test_plain_string_passthrough(self):
        assert OptionalConstructor(str)("hello") == "hello"

    def test_empty_string_str_returns_none(self):
        assert OptionalConstructor(str)("") is None


class TestChoices:
    def test_valid_choice(self):
        assert ChoicesConstructor("red", "green")("red") == "red"

    def test_invalid_choice_raises(self):
        with pytest.raises(ValueError):
            ChoicesConstructor("red", "green")("blue")

    def test_case_insensitive_returns_canonical(self):
        assert ChoicesConstructor("red", "green", caseSensitive=False)("RED") == "red"

    def test_case_sensitive_rejects_wrong_case(self):
        with pytest.raises(ValueError):
            ChoicesConstructor("red", caseSensitive=True)("RED")

    def test_error_message_contains_choices(self):
        with pytest.raises(ValueError, match="red"):
            ChoicesConstructor("red", "green")("blue")


class Color(Enum):
    RED = 1
    GREEN = 2


class TestEnum:

    def test_valid_name(self):
        assert ChoicesConstructor.from_enum(Color)("RED") == Color.RED

    def test_case_insensitive(self):
        assert ChoicesConstructor.from_enum(Color, caseSensitive=False)("red") == Color.RED

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError):
            ChoicesConstructor.from_enum(Color)("BLUE")

    def test_case_sensitive_rejects_wrong_case(self):
        with pytest.raises(ValueError):
            ChoicesConstructor.from_enum(Color, caseSensitive=True)("red")

    def test_error_message_contains_members(self):
        with pytest.raises(ValueError, match="RED"):
            ChoicesConstructor.from_enum(Color)("BLUE")
