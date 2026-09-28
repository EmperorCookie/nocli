from typing import Annotated

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
    assert cli.run(["--flag", "purple"]) == 2, "Expected exit code `2` for a strict bool parse error"


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


def test_bool_permissive_opt_in():
    def fn(
        *,
        flag: Annotated[
            bool,
            nocli.CliConfig(constructor=nocli.constructors.BoolConstructor(invalid=False)),
        ] = False,
    ) -> int:
        return 1 if flag else 0

    cli = nocli.Cli(fn)
    assert cli.run(["--flag", "purple"]) == 0
    assert cli.run(["--flag", "true"]) == 1


def test_optional_bool():
    def fn(*, flag: bool | None = None) -> int:
        if flag is None:
            return 0
        return 1 if flag else 2

    cli = nocli.Cli(fn)
    assert cli.run(["--flag", "true"]) == 1
    assert cli.run(["--flag", "false"]) == 2
    assert cli.run(["--flag", ""]) == 0, "Expected `None` for an empty (falsy) value"
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


def test_non_callable_annotation_raises():
    # Only applies when no custom constructor is registered for the type (not yet implemented).
    def fn(value: 42) -> int:  # type: ignore # That's what's being tested
        return value

    with pytest.raises(nocli.NoConstructorError):
        nocli.Cli(fn)


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
