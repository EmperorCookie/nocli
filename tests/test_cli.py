import functools
import inspect
from enum import Enum
from typing import Annotated, Literal

import pytest

import nocli


def test_positional_str():
    def fn(value: str) -> int:
        return len(value)

    assert nocli.Cli(fn).run(["hello"]) == 5


def test_positional_int():
    def fn(value: int) -> int:
        return value

    assert nocli.Cli(fn).run(["42"]) == 42


def test_multiple_positional():
    def fn(value: str, offset: int) -> int:
        return len(value) + offset

    assert nocli.Cli(fn).run(["foo", "7"]) == 10


def test_keyword_default_unused():
    def fn(*, value: int = 10) -> int:
        return value

    assert nocli.Cli(fn).run([]) == 10


def test_keyword_default_overridden():
    def fn(*, value: int = 10) -> int:
        return value

    assert nocli.Cli(fn).run(["--value", "99"]) == 99


def test_positional_and_keyword():
    captured = []

    def fn(value: str, *, count: int = 1) -> int:
        captured.append((value, count))
        return 0

    cli = nocli.Cli(fn)
    cli.run(["alice"])
    assert captured[-1] == ("alice", 1)
    cli.run(["alice", "--count", "3"])
    assert captured[-1] == ("alice", 3)


def test_bool_strict_by_default():
    def fn(*, flag: bool = False) -> int:
        return 1 if flag else 0

    cli = nocli.Cli(fn)
    assert cli.run(["--flag", "true"]) == 1
    assert cli.run(["--flag", "0"]) == 0
    assert cli.run(["--flag", "purple"]) == 2, (
        "Expected exit code `2` for a strict bool parse error"
    )


def test_bool_deny_tokens_cannot_open_gate():
    executed = []

    def drop(path: str, *, confirm: bool = False) -> int:
        if confirm:
            executed.append(path)
        return 0

    cli = nocli.Cli(drop)
    for token in ("false", "no", "off", "f", "n", "0", "FALSE"):
        executed.clear()
        assert cli.run(["/etc/passwd", "--confirm", token]) == 0
        assert not executed, f"Gate opened for deny token `{token}`"


def test_bool_permissive():
    def fn(
        *,
        flag: Annotated[
            bool,
            nocli.CliConfig(
                constructor=nocli.constructors.BoolConstructor(invalidFinalizer=lambda _: False)
            ),
        ] = False,
    ) -> int:
        return 1 if flag else 0

    cli = nocli.Cli(fn)
    assert cli.run(["--flag", "purple"]) == 0
    assert cli.run(["--flag", "true"]) == 1


def test_bool_none():
    def fn(*, flag: bool | None = None) -> int:
        if flag is None:
            return 0
        return 1 if flag else 2

    cli = nocli.Cli(fn)
    assert cli.run(["--flag", "true"]) == 1
    assert cli.run(["--flag", "false"]) == 2
    assert cli.run(["--flag", ""]) == 2, "A trailing `None` is never parsed"
    assert cli.run([]) == 0


def test_no_annotation_defaults_to_str():
    def fn(value) -> int:
        if isinstance(value, str):
            return 0
        return 1

    assert nocli.Cli(fn).run(["hello"]) == 0


def test_docstring_used_as_description():
    def fn() -> int:
        """Does something useful."""
        return 0

    assert nocli.Cli(fn).description == "Does something useful."


def test_no_docstring_gives_no_description():
    def fn() -> int:
        return 0

    assert nocli.Cli(fn).description is None


def test_multiline_docstring_cleaned():
    def fn() -> int:
        """
        First line.

        Second paragraph.
        """
        return 0

    assert nocli.Cli(fn).description == "First line.\n\nSecond paragraph."


def test_no_constructor():
    def fn(value: 42) -> int:  # type: ignore # That's what's being tested
        return value

    with pytest.raises(nocli.exceptions.ParamConstructorError) as e:
        nocli.Cli(fn)
    assert e.value.parameter == "value"
    assert isinstance(e.value.cause, nocli.exceptions.NoConstructorError)


def test_shape_error_names_parameter():
    def fn(first: int, second: list[int] | int = 0) -> int:
        return 0

    with pytest.raises(nocli.exceptions.ParamConstructorError) as e:
        nocli.Cli(fn)
    assert e.value.parameter == "second"
    assert isinstance(e.value.cause, nocli.exceptions.ConstructorShapeError)


@pytest.mark.parametrize("error", [ValueError, TypeError, KeyError])
def test_construction_failure_is_parse_error(error):
    def boom(value):
        raise error("boom")

    fn = opt(str, "", nocli.CliConfig(constructor=boom))
    assert nocli.Cli(fn).run(["--val", "x"]) == 2


def test_case_sensitive_by_default():
    def fn(*, value: str = "") -> int:
        return len(value)

    assert nocli.Cli(fn).run(["--VALUE", "result"]) == 2, "Expected exit code `2` for parsing error"


def test_case_insensitive_matches_flag_name():
    def fn(*, value: str = "") -> int:
        return len(value)

    assert nocli.Cli(fn, caseSensitive=False).run(["--VALUE", "result"]) == 6


def test_case_insensitive_preserves_value():
    def fn(*, value: str = "") -> int:
        return len(value)

    assert nocli.Cli(fn, caseSensitive=False).run(["--value", "Hello"]) == 5


def test_main_exits_with_return_value(monkeypatch):
    def fn() -> int:
        return 0

    monkeypatch.setattr("sys.argv", ["prog"])
    with pytest.raises(SystemExit) as exc:
        nocli.Cli(fn).main()
    assert exc.value.code == 0


def test_main_exits_with_nonzero_return_value(monkeypatch):
    def fn() -> int:
        return 1

    monkeypatch.setattr("sys.argv", ["prog"])
    with pytest.raises(SystemExit) as exc:
        nocli.Cli(fn).main()
    assert exc.value.code == 1


# dict[<length>, dict[CaseType, <name>]]
_WORDS = ("output", "dir", "file", "ext")
_CASE_TYPE_DATA = {
    i: {
        nocli.CaseType.KEBAB: "-".join(_WORDS[:i]).lower(),
        nocli.CaseType.KEBAB_UPPER: "-".join(_WORDS[:i]).upper(),
        nocli.CaseType.SNAKE: "_".join(_WORDS[:i]).lower(),
        nocli.CaseType.SNAKE_UPPER: "_".join(_WORDS[:i]).upper(),
        nocli.CaseType.CAMEL: "".join([_WORDS[0].lower(), *(w.capitalize() for w in _WORDS[1:i])]),
        nocli.CaseType.PASCAL: "".join(w.capitalize() for w in _WORDS[:i]),
    }
    for i in range(1, 5)
}

# For each length, test each `CaseType` against all other `CaseType`s, including no change
_CASE_TYPE_CASES = [
    pytest.param(
        value, expectedCase, expected, id=f"{length}-{valueCase.name}-to-{expectedCase.name}"
    )
    for length, cases in _CASE_TYPE_DATA.items()
    for valueCase, value in cases.items()
    for expectedCase, expected in cases.items()
]

_EDGE_CASE_DATA = {
    name: {i: f"{prefix}{data[nocli.CaseType.CAMEL]}" for i, data in _CASE_TYPE_DATA.items()}
    for name, prefix in {
        "underscore": "_",
        "dunderscore": "__",
    }.items()
}

_EDGE_CASES = [
    pytest.param(value, expectedCase, expected, id=f"{length}-{name}-to-{expectedCase.name}")
    for name, values in _EDGE_CASE_DATA.items()
    for length, value in values.items()
    for expectedCase, expected in _CASE_TYPE_DATA[length].items()
]


@pytest.mark.parametrize("value, expectedCase, expected", _CASE_TYPE_CASES + _EDGE_CASES)
def test_derive_flag_name(value: str, expectedCase: nocli.CaseType, expected: str):
    assert expectedCase.convert(value) == expected


class Color(Enum):
    RED = 1
    GREEN = 2


class Tag(nocli.constructors.ConstructorAbc):
    """Claims `int` annotations and tags what it constructs."""

    @classmethod
    def can_handle(cls, annotation):
        return annotation is int

    @classmethod
    def resolve(cls, annotation):
        yield from ()
        return cls(lambda value: ("tag", value))


def make(kind, annotation, default, config):
    if config is not None:
        annotation = Annotated[annotation, config]

    def fn(**kwargs):
        return 0

    param = inspect.Parameter("val", kind, default=default, annotation=annotation)
    fn.__signature__ = inspect.Signature([param])
    return fn


def opt(annotation, default=None, config=None):
    """A function with a single keyword-only option `x`."""
    return make(inspect.Parameter.KEYWORD_ONLY, annotation, default, config)


def pos(annotation, config=None):
    """A function with a single positional `x`."""
    return make(
        inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation, inspect.Parameter.empty, config
    )


def got(fn, *argv, **options):
    """Runs a `Cli` for `fn` and returns the keyword arguments that `fn` was called with."""
    calls = []

    @functools.wraps(fn)
    def spy(**kwargs):
        calls.append(kwargs)
        return 0

    assert nocli.Cli(spy, **options).run(list(argv)) == 0
    return calls[-1]


def row(text, token="--val"):
    """The help line that holds `token`, without indentation."""
    return next(line for line in text.splitlines() if token in line).strip()


class TestCli:
    def test_custom(self):
        cli = {"constructors": [Tag, *nocli.DEFAULT_CONSTRUCTORS]}
        assert got(opt(int, 0), "--val", "5", **cli) == {"val": ("tag", "5")}

    def test_custom_nested(self):
        cli = {"constructors": [Tag, *nocli.DEFAULT_CONSTRUCTORS]}
        assert got(opt(list[int]), "--val", "1", "--val", "2", **cli) == {
            "val": [("tag", "1"), ("tag", "2")]
        }

    def test_replaced(self):
        with pytest.raises(nocli.exceptions.ParamConstructorError) as e:
            nocli.Cli(opt(int, 0), constructors=[nocli.constructors.BoolConstructor])
        assert isinstance(e.value.cause, nocli.exceptions.NoConstructorError)
        assert e.value.cause.annotation is int

    def test_property(self):
        cli = nocli.Cli(opt(int, 0), constructors=[Tag, nocli.constructors.CallableConstructor])
        assert cli.constructors == (Tag, nocli.constructors.CallableConstructor)

    def test_default_property(self):
        assert nocli.Cli(opt(int, 0)).constructors == tuple(nocli.DEFAULT_CONSTRUCTORS)

    def test_catch_all_last(self):
        assert nocli.DEFAULT_CONSTRUCTORS[-1] is nocli.constructors.CallableConstructor

    def test_snapshot(self):
        cli = nocli.Cli(opt(int, 0))
        nocli.DEFAULT_CONSTRUCTORS.insert(0, Tag)
        try:
            assert Tag not in cli.constructors
            assert Tag in nocli.Cli(opt(int, 0)).constructors
        finally:
            nocli.DEFAULT_CONSTRUCTORS.remove(Tag)

    @pytest.mark.parametrize(
        ("annotation", "argv", "expected"),
        [
            (int | str, ["5"], 5),
            (int | str, ["x"], "x"),
            (str | int, ["5"], "5"),
            (int | Literal["auto"], ["auto"], "auto"),
            (None | int, [""], None),
            (None | int, ["5"], 5),
            (int | None, ["5"], 5),
            (list[int], ["1", "--val", "2"], [1, 2]),
            (tuple[int, int], ["1", "2"], (1, 2)),
            (tuple[int, ...], ["1", "--val", "2"], (1, 2)),
            (set[int], ["1", "--val", "1"], {1}),
            (dict[str, int], ["a", "1", "--val", "b", "2"], {"a": 1, "b": 2}),
            (list[tuple[int, int]], ["1", "2", "--val", "3", "4"], [(1, 2), (3, 4)]),
            (list[int | Literal["all"]], ["1", "--val", "all"], [1, "all"]),
            (Color, ["GREEN"], Color.GREEN),
        ],
    )
    def test_types(self, annotation, argv, expected):
        assert got(opt(annotation), "--val", *argv) == {"val": expected}

    def test_positional_union(self):
        assert got(pos(int | str), "5") == {"val": 5}

    def test_absent(self):
        assert got(opt(int | None, 3)) == {}

    def test_trailing_none_unparsed(self):
        assert nocli.Cli(opt(int | None)).run(["--val", ""]) == 2

    def test_no_member_matches(self):
        assert nocli.Cli(opt(int | float)).run(["--val", "abc"]) == 2

    def test_flag(self):
        fn = opt(bool, False, nocli.CliConfig(constructor=nocli.constructors.FlagConstructor()))
        assert got(fn, "--val") == {"val": True}
        assert got(fn) == {}

    def test_flag_count(self):
        config = nocli.CliConfig(
            constructor=nocli.constructors.IterableConstructor(
                nocli.constructors.FlagConstructor(), list
            )
        )
        fn = opt(list[bool], (), config)
        assert got(fn, "--val", "--val", "--val") == {"val": [True, True, True]}

    def test_plain_flag(self):
        fn = opt(str, "", nocli.CliConfig(constructor=lambda: "on", count=0))
        assert got(fn, "--val") == {"val": "on"}

    def test_flag_value(self):
        fn = opt(str, "", nocli.CliConfig(constructor=nocli.constructors.FlagConstructor("on")))
        assert got(fn, "--val") == {"val": "on"}

    def test_single(self):
        fn = opt(list[tuple[int, int]], config=nocli.CliConfig(repeatable=False))
        assert got(fn, "--val", "1", "2") == {"val": [(1, 2)]}

    def test_single_once(self):
        fn = opt(list[int], config=nocli.CliConfig(repeatable=False))
        assert nocli.Cli(fn).run(["--val", "1", "--val", "2"]) == 2

    def test_single_ok(self):
        fn = opt(int, config=nocli.CliConfig(repeatable=False))
        assert got(fn, "--val", "3") == {"val": 3}

    def test_plain_count(self):
        fn = opt(str, config=nocli.CliConfig(constructor=lambda value: value, count=2))
        assert got(fn, "--val", "a", "b") == {"val": ("a", "b")}

    def test_plain_repeatable(self):
        fn = opt(str, config=nocli.CliConfig(constructor=list, repeatable=True))
        assert got(fn, "--val", "a", "--val", "b") == {"val": ["a", "b"]}

    @pytest.mark.parametrize(
        ("config", "member"),
        [
            (nocli.CliConfig(count=2), "count"),
            (nocli.CliConfig(repeatable=True), "repeatable"),
        ],
    )
    def test_owned(self, config, member):
        with pytest.raises(nocli.exceptions.ConfigConflictError) as e:
            nocli.Cli(opt(int, 0, config))
        assert (e.value.parameter, e.value.member) == ("val", member)

    def test_owned_constructor(self):
        config = nocli.CliConfig(constructor=nocli.constructors.FlagConstructor(), count=1)
        with pytest.raises(nocli.exceptions.ConfigConflictError):
            nocli.Cli(opt(bool, False, config))

    @pytest.mark.parametrize(
        "config", [nocli.CliConfig(displayName=""), nocli.CliConfig(displayName="_")]
    )
    def test_empty_name(self, config):
        with pytest.raises(nocli.exceptions.InvalidNameError) as e:
            nocli.Cli(opt(int, 0, config))
        assert e.value.parameter == "val"

    def test_empty_name_positional(self):
        with pytest.raises(nocli.exceptions.InvalidNameError):
            nocli.Cli(pos(int, nocli.CliConfig(displayName="")))

    def test_empty_alias(self):
        with pytest.raises(nocli.exceptions.InvalidNameError) as e:
            nocli.Cli(opt(int, 0, nocli.CliConfig(aliases=("",))))
        assert e.value.name == ""

    def test_no_flags(self):
        with pytest.raises(nocli.exceptions.NoFlagsError) as e:
            nocli.Cli(opt(int, 0, nocli.CliConfig(flags=())))
        assert e.value.parameter == "val"

    def test_no_default_flags(self):
        with pytest.raises(nocli.exceptions.NoFlagsError):
            nocli.Cli(opt(int, 0), defaultFlags=False)

    def test_var_args(self):
        def fn(*args: int) -> int:
            return 0

        with pytest.raises(nocli.exceptions.UnsupportedParameterError) as e:
            nocli.Cli(fn)
        assert (e.value.parameter, e.value.kind) == ("args", inspect.Parameter.VAR_POSITIONAL)

    def test_var_kwargs(self):
        def fn(**kwargs: int) -> int:
            return 0

        with pytest.raises(nocli.exceptions.UnsupportedParameterError) as e:
            nocli.Cli(fn)
        assert (e.value.parameter, e.value.kind) == ("kwargs", inspect.Parameter.VAR_KEYWORD)


class TestHelp:
    @pytest.mark.parametrize(
        ("annotation", "shown"),
        [
            (str, "<str> (default: None)"),
            (inspect.Parameter.empty, "<str> (default: None)"),
            (int | Literal["auto"], "<int | 'auto'> (default: None)"),
            (int | None, "<int> (default: None)"),
            (None | int, "<None | int> (default: None)"),
            (tuple[int, int], "<(int, int)> (default: None)"),
            (Literal["a", "b"], "<'a' | 'b'> (default: None)"),
            (Color, "<'RED' | 'GREEN'> (default: None)"),
            (list[int], "<list[int]> (repeatable, default: None)"),
            (list[tuple[int, int]], "<list[(int, int)]> (repeatable, default: None)"),
            (dict[str, int], "<dict[(str, int)]> (repeatable, default: None)"),
        ],
    )
    def test_type(self, usage, annotation, shown):
        assert row(usage(nocli.Cli(opt(annotation)))) == f"--val {shown}"

    def test_choices_in_type(self, usage):
        assert "Choices:" not in usage(nocli.Cli(opt(Color, Color.RED)))

    def test_insensitive(self, usage):
        config = nocli.CliConfig(
            constructor=nocli.constructors.ChoicesConstructor("a", "b", caseSensitive=False)
        )
        assert "<choices<ins>['a' | 'b']>" in usage(nocli.Cli(opt(str, "a", config)))

    def test_flag(self, usage):
        config = nocli.CliConfig(constructor=nocli.constructors.FlagConstructor())
        assert row(usage(nocli.Cli(opt(bool, False, config)))) == "--val (flag, default: False)"

    def test_display_type(self, usage):
        config = nocli.CliConfig(displayType="FILE")
        assert row(usage(nocli.Cli(opt(str, "a", config)))) == "--val <FILE> (default: 'a')"

    def test_display_type_empty(self, usage):
        config = nocli.CliConfig(displayType="")
        assert row(usage(nocli.Cli(opt(str, "a", config)))) == "--val (default: 'a')"

    def test_required(self, usage):
        config = nocli.CliConfig(flags=("val",))
        text = usage(nocli.Cli(opt(int, inspect.Parameter.empty, config)))
        assert row(text) == "--val <int> (required)"

    def test_positional(self, usage):
        assert row(usage(nocli.Cli(pos(int))), "[val") == "[val <int> (required)]"

    def test_default(self, usage):
        assert row(usage(nocli.Cli(opt(int, 3)))) == "--val <int> (default: 3)"

    def test_default_str(self, usage):
        assert row(usage(nocli.Cli(opt(str, "hi")))) == "--val <str> (default: 'hi')"

    def test_factory(self, usage):
        config = nocli.CliConfig(defaultFactory=lambda: 7)
        assert row(usage(nocli.Cli(opt(int, 0, config)))) == "--val <int> (default: 7)"

    def test_display_default(self, usage):
        config = nocli.CliConfig(displayDefault="$HOME")
        assert row(usage(nocli.Cli(opt(str, "a", config)))) == "--val <str> (default: $HOME)"

    def test_display_default_wins(self, usage):
        def never():
            raise AssertionError("The factory must not be called")

        config = nocli.CliConfig(displayDefault="$HOME", defaultFactory=never)
        assert row(usage(nocli.Cli(opt(str, "a", config)))) == "--val <str> (default: $HOME)"

    def test_display_default_empty(self, usage):
        config = nocli.CliConfig(displayDefault="")
        assert row(usage(nocli.Cli(opt(str, "a", config)))) == "--val <str>"

    def test_display_default_quoted(self, usage):
        config = nocli.CliConfig(displayDefault='""')
        assert row(usage(nocli.Cli(opt(str, "", config)))) == '--val <str> (default: "")'
