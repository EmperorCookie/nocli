import pytest

from nocli import (
    DuplicateFlagError,
    FlagAlreadyPassedError,
    MissingOptionError,
    MissingValueError,
    Parser,
    ParserOption,
    UnexpectedTokenError,
    UnrecognizedTokenError,
)


@pytest.fixture
def make_option():
    def _factory(name, flags=None, required=True):
        return ParserOption(
            name=name,
            flags=flags or [],
            required=required,
            constructor=str,
            count=1,
            repeatable=False,
            sticky=False,
            stickyStopFlag=None,
            exception=None,
        )

    return _factory


# --- Exceptions ---


class TestDuplicateFlagError:
    def test_flags_property(self):
        e = DuplicateFlagError(["--foo", "-f"])
        assert e.flags == ["--foo", "-f"]

    def test_message_contains_flags(self):
        e = DuplicateFlagError(["--foo"])
        assert "--foo" in e.message


class TestFlagAlreadyPassedError:
    def test_flag_property(self):
        assert FlagAlreadyPassedError("--foo", "bar").flag == "--foo"

    def test_value_property(self):
        assert FlagAlreadyPassedError("--foo", "bar").value == "bar"

    def test_message_contains_flag(self):
        assert "--foo" in FlagAlreadyPassedError("--foo", "bar").message


class TestMissingValueError:
    def test_found_property(self):
        assert MissingValueError("found", 1, 3).found == 1

    def test_expected_property(self):
        assert MissingValueError("expected", 1, 3).expected == 3

    def test_message_contains_both_counts(self):
        e = MissingValueError("message", 1, 3)
        assert "1" in e.message and "3" in e.message


class TestUnrecognizedTokenError:
    def test_token_property(self):
        assert UnrecognizedTokenError("--typo").token == "--typo"


class TestUnexpectedTokenError:
    def test_token_property(self):
        assert UnexpectedTokenError("extra").token == "extra"


class TestMissingError:
    def test_missing_property(self, make_option):
        opts = [make_option("foo")]
        assert list(MissingOptionError(opts).missing) == opts

    def test_missing_names(self, make_option):
        opts = [make_option("foo"), make_option("bar")]
        assert MissingOptionError(opts).missingNames == ["foo", "bar"]

    def test_missing_flags_or_names_uses_first_flag(self, make_option):
        opt = make_option("foo", flags=["--foo", "-f"])
        assert MissingOptionError([opt]).missingFlagsOrNames == ["--foo"]

    def test_missing_flags_or_names_falls_back_to_name(self, make_option):
        opt = make_option("foo")
        assert MissingOptionError([opt]).missingFlagsOrNames == ["foo"]


# --- ParserOption ---


class TestParserOption:
    def test_count_negative_raises(self):
        with pytest.raises(ValueError):
            ParserOption(
                name="x",
                flags=[],
                required=False,
                constructor=str,
                count=-1,
                repeatable=False,
                sticky=False,
                stickyStopFlag=None,
                exception=None,
            )

    def test_count_zero_valid(self):
        opt = ParserOption(
            name="x",
            flags=["--x"],
            required=False,
            constructor=str,
            count=0,
            repeatable=False,
            sticky=False,
            stickyStopFlag=None,
            exception=None,
        )
        assert opt.count == 0


# --- hasPositionals ---


@pytest.mark.parametrize(
    "flags,expected",
    [
        (None, True),
        (["--foo"], False),
    ],
)
def test_has_positionals(flags, expected):
    p = Parser()
    p.add_option("foo", flags=flags)
    assert p.hasPositionals is expected


def test_has_positionals_empty():
    assert Parser().hasPositionals is False


# --- add_option ---


class TestAddOption:
    def test_returns_self(self):
        p = Parser()
        assert p.add_option("foo") is p

    def test_positional_reflected_in_has_positionals(self):
        p = Parser()
        p.add_option("foo")
        assert p.hasPositionals is True

    def test_flag_option_not_reflected_in_has_positionals(self):
        p = Parser()
        p.add_option("foo", flags=["--foo"])
        assert p.hasPositionals is False

    def test_duplicate_flag_raises(self):
        p = Parser()
        p.add_option("foo", flags=["--foo", "-f"])
        with pytest.raises(DuplicateFlagError) as exc:
            p.add_option("bar", flags=["--bar", "-f"])
        assert "-f" in exc.value.flags

    def test_duplicate_flag_case_insensitive(self):
        p = Parser(caseSensitive=False)
        p.add_option("foo", flags=["--foo"])
        with pytest.raises(DuplicateFlagError):
            p.add_option("bar", flags=["--FOO"])

    def test_duplicate_flag_case_sensitive_allowed(self):
        p = Parser(caseSensitive=True)
        p.add_option("foo", flags=["--foo"])
        p.add_option("bar", flags=["--FOO"])

    def test_fluent_chaining(self):
        p = Parser()
        assert p.add_option("a").add_option("b") is p


# --- _get_missing ---


class TestGetMissing:
    @pytest.fixture
    def parser_with(self):
        def _factory(*options):
            p = Parser()
            for kwargs in options:
                p.add_option(**kwargs)
            return p

        return _factory

    def test_nothing_missing_when_all_provided(self, parser_with):
        p = parser_with({"name": "foo", "flags": ["--foo"], "required": True})
        assert p._get_missing([], {"foo": "x"}) == []

    def test_required_flag_missing(self, parser_with):
        p = parser_with({"name": "foo", "flags": ["--foo"], "required": True})
        missing = p._get_missing([], {})
        assert len(missing) == 1 and missing[0].name == "foo"

    def test_optional_flag_not_reported(self, parser_with):
        p = parser_with({"name": "foo", "flags": ["--foo"], "required": False})
        assert p._get_missing([], {}) == []

    def test_required_positional_missing(self, parser_with):
        p = parser_with({"name": "pos", "required": True})
        missing = p._get_missing([], {})
        assert len(missing) == 1 and missing[0].name == "pos"

    def test_positional_not_missing_when_provided(self, parser_with):
        p = parser_with({"name": "pos", "required": True})
        assert p._get_missing(["x"], {}) == []

    def test_second_positional_missing(self, parser_with):
        p = parser_with({"name": "a", "required": True}, {"name": "b", "required": True})
        missing = p._get_missing(["x"], {})
        assert len(missing) == 1 and missing[0].name == "b"

    def test_mixed_missing(self, parser_with):
        p = parser_with(
            {"name": "pos", "required": True},
            {"name": "flag", "flags": ["--flag"], "required": True},
        )
        assert {o.name for o in p._get_missing([], {})} == {"pos", "flag"}
