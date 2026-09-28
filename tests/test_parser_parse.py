import pytest
from unittest.mock import MagicMock

from nocli._parser import (
    FlagAlreadyPassedError,
    MissingOptionError,
    MissingValueError,
    Parser,
    UnexpectedTokenError,
    UnrecognizedTokenError,
)


class TestParsePositionals:
    def test_single_required(self):
        p = Parser()
        p.add_option("x", required=True)
        args, _ = p.parse(["hello"])
        assert args == ["hello"]

    def test_multiple_required(self):
        p = Parser()
        p.add_option("a", required=True)
        p.add_option("b", required=True)
        args, _ = p.parse(["foo", "bar"])
        assert args == ["foo", "bar"]

    def test_constructor_applied(self):
        p = Parser()
        p.add_option("n", constructor=int)
        args, _ = p.parse(["42"])
        assert args == [42]

    def test_optional_provided(self):
        p = Parser()
        p.add_option("x")
        args, _ = p.parse(["val"])
        assert args == ["val"]

    def test_optional_absent(self):
        p = Parser()
        p.add_option("x")
        args, _ = p.parse([])
        assert args == []

    def test_required_missing_raises(self):
        p = Parser()
        p.add_option("x", required=True)
        with pytest.raises(MissingOptionError) as exc:
            p.parse([])
        assert "x" in exc.value.missingNames

    def test_second_required_missing_raises(self):
        p = Parser()
        p.add_option("a", required=True)
        p.add_option("b", required=True)
        with pytest.raises(MissingOptionError) as exc:
            p.parse(["foo"])
        assert "b" in exc.value.missingNames


class TestParseFlags:
    def test_single_flag(self):
        p = Parser()
        p.add_option("out", flags=["--out"])
        _, kwargs = p.parse(["--out", "result"])
        assert kwargs == {"out": "result"}

    def test_flag_absent(self):
        p = Parser()
        p.add_option("out", flags=["--out"])
        _, kwargs = p.parse([])
        assert kwargs == {}

    def test_required_flag_missing_raises(self):
        p = Parser()
        p.add_option("out", flags=["--out"], required=True)
        with pytest.raises(MissingOptionError) as exc:
            p.parse([])
        assert "out" in exc.value.missingNames

    def test_short_flag(self):
        p = Parser()
        p.add_option("out", flags=["--out", "-o"])
        _, kwargs = p.parse(["-o", "result"])
        assert kwargs["out"] == "result"

    def test_boolean_flag(self):
        p = Parser()
        p.add_option("verbose", flags=["--verbose"], count=0, constructor=bool)
        _, kwargs = p.parse(["--verbose"])
        assert kwargs["verbose"] is True

    def test_boolean_flag_absent(self):
        p = Parser()
        p.add_option("verbose", flags=["--verbose"], count=0)
        _, kwargs = p.parse([])
        assert kwargs == {}

    def test_multi_value_flag(self):
        p = Parser()
        p.add_option("pt", flags=["--pt"], count=2, constructor=lambda v: (int(v[0]), int(v[1])))
        _, kwargs = p.parse(["--pt", "3", "7"])
        assert kwargs["pt"] == (3, 7)

    def test_multi_value_truncated_raises(self):
        p = Parser()
        p.add_option("pt", flags=["--pt"], count=2)
        with pytest.raises(MissingValueError):
            p.parse(["--pt", "3"])

    def test_case_insensitive(self):
        p = Parser(caseSensitive=False)
        p.add_option("out", flags=["--out"])
        _, kwargs = p.parse(["--OUT", "result"])
        assert kwargs["out"] == "result"

    def test_case_sensitive_no_match(self):
        p = Parser(caseSensitive=True)
        p.add_option("out", flags=["--out"], required=True)
        with pytest.raises(UnrecognizedTokenError):
            p.parse(["--OUT", "result"])

    def test_constructor_applied(self):
        p = Parser()
        p.add_option("n", flags=["--n"], constructor=int)
        _, kwargs = p.parse(["--n", "5"])
        assert kwargs["n"] == 5


class TestParseDuplicates:
    def test_duplicate_raises_by_default(self):
        p = Parser()
        p.add_option("x", flags=["--x"])
        with pytest.raises(FlagAlreadyPassedError) as exc:
            p.parse(["--x", "a", "--x", "b"])
        assert exc.value.flag == "--x"
        assert exc.value.value == "a"

    def test_duplicate_overwrites_when_allowed(self):
        p = Parser(allowDuplicates=True)
        p.add_option("x", flags=["--x"])
        _, kwargs = p.parse(["--x", "a", "--x", "b"])
        assert kwargs["x"] == "b"

    def test_array_allows_multiple(self):
        p = Parser()
        p.add_option("x", flags=["--x"], repeatable=True)
        _, kwargs = p.parse(["--x", "a", "--x", "b"])
        assert kwargs["x"] == ["a", "b"]


class TestParseArrays:
    def test_flag_array_accumulates(self):
        p = Parser()
        p.add_option("tag", flags=["--tag"], repeatable=True)
        _, kwargs = p.parse(["--tag", "a", "--tag", "b", "--tag", "c"])
        assert kwargs["tag"] == ["a", "b", "c"]

    def test_flag_array_single_invocation(self):
        p = Parser()
        p.add_option("tag", flags=["--tag"], repeatable=True)
        _, kwargs = p.parse(["--tag", "only"])
        assert kwargs["tag"] == ["only"]

    def test_positional_array(self):
        p = Parser()
        p.add_option("items", repeatable=True, sticky=True)
        args, _ = p.parse(["a", "b", "c"])
        assert args == [["a", "b", "c"]]


class TestParseDicts:
    def test_dict_array_accumulates(self):
        p = Parser()
        p.add_option(
            "map",
            flags=["--map"],
            constructor=lambda vs: {k: v for k, v in vs},
            count=2,
            repeatable=True,
        )
        _, kwargs = p.parse(["--map", "a", "1", "--map", "b", "2", "--map", "c", "3"])
        assert kwargs["map"] == {"a": "1", "b": "2", "c": "3"}

    def test_dict_array_single_invocation(self):
        p = Parser()
        p.add_option(
            "map",
            flags=["--map"],
            constructor=lambda vs: {k: v for k, v in vs},
            count=2,
            repeatable=True,
        )
        _, kwargs = p.parse(["--map", "a", "1"])
        assert kwargs["map"] == {"a": "1"}

    def test_positional_dict_array(self):
        p = Parser()
        p.add_option(
            "map",
            constructor=lambda vs: {k: v for k, v in vs},
            count=2,
            repeatable=True,
            sticky=True,
        )
        args, _ = p.parse(["a", "1", "b", "2", "c", "3"])
        assert args == [{"a": "1", "b": "2", "c": "3"}]


class TestParseSticky:
    def test_sticky_positional_collects_until_end(self):
        p = Parser()
        p.add_option("files", repeatable=True, sticky=True)
        args, _ = p.parse(["a", "b", "c"])
        assert args == [["a", "b", "c"]]

    def test_sticky_not_interrupted_by_new(self):
        p = Parser()
        p.add_option("files", flags=["--files"], repeatable=True, sticky=True)
        p.add_option("out", flags=["--out"])
        _, kwargs = p.parse(["--files", "a", "b", "c", "--out", "result"])
        assert kwargs["files"] == ["a", "b", "c", "--out", "result"]
        assert "out" not in kwargs

    def test_sticky_not_interrupted_by_flag(self):
        p = Parser()
        p.add_option("files", flags=["--files"], repeatable=True, sticky=True)
        p.add_option("verbose", flags=["--verbose"], count=0, constructor=bool)
        _, kwargs = p.parse(["--files", "a", "b", "--verbose"])
        assert kwargs["files"] == ["a", "b", "--verbose"]
        assert "verbose" not in kwargs

    def test_sticky_interrupted_by_stop_flag(self):
        p = Parser()
        p.add_option("sticky", repeatable=True, sticky=True, stickyStopFlag="--")
        p.add_option("positional")
        args, _ = p.parse(["a", "b", "--", "c"])
        assert args == [["a", "b"], "c"]

    def test_two_options_with_different_stop_flags(self):
        p = Parser()
        p.add_option("files", flags=["--files"], repeatable=True, sticky=True, stickyStopFlag="--")
        p.add_option("items", flags=["--items"], repeatable=True, sticky=True, stickyStopFlag="::")
        p.add_option("rest", repeatable=True)
        args, kwargs = p.parse(["--files", "a", "b", "--", "--items", "x", "y", "::", "tail"])
        assert kwargs["files"] == ["a", "b"]
        assert kwargs["items"] == ["x", "y"]
        assert args == [["tail"]]

    def test_stop_flag_applies_only_to_its_option(self):
        p = Parser()
        p.add_option("files", flags=["--files"], repeatable=True, sticky=True, stickyStopFlag="--")
        p.add_option("raw", flags=["--raw"], repeatable=True, sticky=True)

        # `--` stops the option that declares it as its stop flag...
        _, kwargs = p.parse(["--files", "a", "b", "--"])
        assert kwargs == {"files": ["a", "b"]}

        # ...but is just another value for the option that doesn't declare one.
        _, kwargs = p.parse(["--raw", "a", "b", "--"])
        assert kwargs == {"raw": ["a", "b", "--"]}


class TestParseExceptionFlag:
    def test_raises_exception_with_constructed_value(self):
        class MyError(Exception):
            pass

        p = Parser()
        p.add_option("help", flags=["--help"], count=0, constructor=bool, exception=MyError)
        with pytest.raises(MyError) as exc:
            p.parse(["--help"])
        assert exc.value.args[0] is True

    def test_constructor_called_once_on_exception_flag(self):
        class MyError(Exception):
            pass

        constructor = MagicMock()
        p = Parser()
        p.add_option("help", flags=["--help"], count=0, constructor=constructor, exception=MyError)
        with pytest.raises(MyError):
            p.parse(["--help"])
        constructor.assert_called_once_with("True")

    def test_exception_value_is_constructor_return(self):
        class MyError(Exception):
            pass

        constructor = MagicMock()
        p = Parser()
        p.add_option("help", flags=["--help"], count=0, constructor=constructor, exception=MyError)
        with pytest.raises(MyError) as exc:
            p.parse(["--help"])
        assert exc.value.args[0] is constructor.return_value

    def test_exception_interrupts_before_required_validation(self):
        class MyError(Exception):
            pass

        p = Parser()
        p.add_option("req", required=True)
        p.add_option("help", flags=["--help"], count=0, exception=MyError)
        with pytest.raises(MyError):
            p.parse(["--help"])

    def test_exception_fires_after_prior_args_set(self):
        class MyError(Exception):
            pass

        p = Parser()
        p.add_option("out", flags=["--out"])
        p.add_option("help", flags=["--help"], count=0, exception=MyError)
        with pytest.raises(MyError):
            p.parse(["--out", "result", "--help"])

    def test_exception_abandons_remaining_argv(self):
        class MyError(Exception):
            pass

        p = Parser()
        p.add_option("help", flags=["--help"], count=0, exception=MyError)
        p.add_option("out", flags=["--out"])
        with pytest.raises(MyError):
            p.parse(["--help", "--out", "result"])

    def test_exception_during_sticky(self):
        class MyError(Exception):
            pass

        p = Parser()
        p.add_option("files", flags=["--files"], repeatable=True, sticky=True)
        p.add_option("help", flags=["--help"], count=0, exception=MyError)

        # Act
        _, kwargs = p.parse(["--files", "a", "b", "--help"])

        # Assert
        assert "help" not in kwargs


class TestParseErrors:
    def test_unrecognized_token_when_required_outstanding(self):
        p = Parser()
        p.add_option("flag1", flags=["--flag1"], required=True)
        p.add_option("flag2", flags=["--flag2"], required=True)
        with pytest.raises(UnrecognizedTokenError) as exc:
            p.parse(["--unknown"])
        assert exc.value.token == "--unknown"

    def test_unexpected_token_when_all_satisfied(self):
        p = Parser()
        p.add_option("x")
        with pytest.raises(UnexpectedTokenError) as exc:
            p.parse(["a", "extra"])
        assert exc.value.token == "extra"

    def test_argv_not_mutated(self):
        p = Parser()
        p.add_option("x")
        original = ["hello"]
        p.parse(original)
        assert original == ["hello"]

    def test_positional_and_flag_together(self):
        p = Parser()
        p.add_option("name", required=True)
        p.add_option("count", flags=["--count"], constructor=int)
        args, kwargs = p.parse(["alice", "--count", "3"])
        assert args == ["alice"]
        assert kwargs == {"count": 3}
