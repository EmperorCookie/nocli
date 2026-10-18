import inspect

import pytest

import nocli

OPTION = nocli.ParserOption(
    name="a",
    flags=["--a"],
    required=True,
    constructor=str,
    count=1,
    repeatable=False,
    sticky=False,
    stickyStopFlag=None,
    exception=None,
)
CAUSE = ValueError("boom")
OWNER = nocli.constructors.FlagConstructor()
FAILURE = (nocli.constructors.CallableConstructor(int), CAUSE)
VAR = inspect.Parameter.VAR_POSITIONAL
NO_CONSTRUCTOR = nocli.exceptions.NoConstructorError(int)

# error, base class, properties
ERRORS = [
    (
        nocli.exceptions.DuplicateFlagError(["--a"]),
        nocli.exceptions.ParserError,
        {"flags": ["--a"]},
    ),
    (
        nocli.exceptions.FlagAlreadyPassedError("--a", "v"),
        nocli.exceptions.ParserError,
        {"flag": "--a", "value": "v"},
    ),
    (
        nocli.exceptions.MissingValueError("opt", 1, 2),
        nocli.exceptions.ParserError,
        {"name": "opt", "found": 1, "expected": 2},
    ),
    (
        nocli.exceptions.UnrecognizedTokenError("x"),
        nocli.exceptions.ParserError,
        {"token": "x"},
    ),
    (
        nocli.exceptions.UnexpectedTokenError("x"),
        nocli.exceptions.ParserError,
        {"token": "x"},
    ),
    (
        nocli.exceptions.MissingOptionError([OPTION]),
        nocli.exceptions.ParserError,
        {"missing": (OPTION,), "missingNames": ["a"], "missingFlagsOrNames": ["--a"]},
    ),
    (
        nocli.exceptions.ConstructionError("loc", int, "v", CAUSE),
        nocli.exceptions.ParserError,
        {"location": "loc", "constructor": int, "value": "v", "cause": CAUSE, "reason": "boom"},
    ),
    (
        nocli.exceptions.DuplicateCommandError("cmd"),
        nocli.exceptions.CliBuildError,
        {"name": "cmd"},
    ),
    (
        nocli.exceptions.NoConstructorError(int),
        nocli.exceptions.CliBuildError,
        {"annotation": int},
    ),
    (
        nocli.exceptions.UnsupportedAnnotationError(nocli.constructors.TupleConstructor, int),
        nocli.exceptions.CliBuildError,
        {"constructor": nocli.constructors.TupleConstructor, "annotation": int},
    ),
    (
        nocli.exceptions.TupleElementShapeError([OWNER]),
        nocli.exceptions.ConstructorShapeError,
        {"constructors": (OWNER,)},
    ),
    (
        nocli.exceptions.IterableElementShapeError(OWNER),
        nocli.exceptions.ConstructorShapeError,
        {"constructors": (OWNER,)},
    ),
    (
        nocli.exceptions.UnionMemberShapeError([OWNER]),
        nocli.exceptions.ConstructorShapeError,
        {"constructors": (OWNER,)},
    ),
    (
        nocli.exceptions.ConfigConflictError("p", "count", 2, OWNER),
        nocli.exceptions.CliBuildError,
        {"parameter": "p", "member": "count", "value": 2, "constructor": OWNER},
    ),
    (
        nocli.exceptions.ParamConstructorError("p", NO_CONSTRUCTOR),
        nocli.exceptions.CliBuildError,
        {"parameter": "p", "cause": NO_CONSTRUCTOR},
    ),
    (
        nocli.exceptions.InvalidNameError("p", ""),
        nocli.exceptions.ParamNameError,
        {"parameter": "p", "name": ""},
    ),
    (
        nocli.exceptions.NoFlagsError("p"),
        nocli.exceptions.ParamNameError,
        {"parameter": "p"},
    ),
    (
        nocli.exceptions.UnsupportedParameterError("p", VAR),
        nocli.exceptions.CliBuildError,
        {"parameter": "p", "kind": VAR},
    ),
    (
        nocli.exceptions.UnionConstructionError("v", [FAILURE]),
        ValueError,
        {"value": "v", "failures": (FAILURE,)},
    ),
]
IDS = [type(error).__name__ for error, _, _ in ERRORS]


@pytest.mark.parametrize(("error", "base", "props"), ERRORS, ids=IDS)
def test_props(error, base, props):
    for name, expected in props.items():
        assert getattr(error, name) == expected


@pytest.mark.parametrize(("error", "base", "props"), ERRORS, ids=IDS)
def test_base(error, base, props):
    assert isinstance(error, base)


@pytest.mark.parametrize(("error", "base", "props"), ERRORS, ids=IDS)
def test_str(error, base, props):
    assert str(error)


@pytest.mark.parametrize(
    "error",
    [e for e, _, _ in ERRORS if isinstance(e, nocli.exceptions.NocliError)],
    ids=lambda e: type(e).__name__,
)
def test_message(error):
    assert error.message == str(error)
