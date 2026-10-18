"""Example CLI. Run with: `python example.py`"""

import enum
import json
from collections.abc import Callable, Generator, Mapping, Sequence
from pathlib import Path
from types import NoneType
from typing import Annotated, Any, Literal
from uuid import UUID

from nocli import DEFAULT_CONSTRUCTORS, CaseType, Cli, CliConfig, Subcommand
from nocli.constructors import (
    BoolConstructor,
    CallableConstructor,
    ChoicesConstructor,
    FlagConstructor,
    HexConstructor,
    HexStringConstructor,
    IntOrHexConstructor,
    IterableConstructor,
    LiteralEvalConstructor,
    OptionalConstructor,
    TupleConstructor,
)

JsonAlias = str | int | float | NoneType | list["JsonAlias"] | dict[str, "JsonAlias"]


class ColorEnum(enum.Enum):
    UNSET = enum.auto()
    RED = enum.auto()
    GREEN = enum.auto()
    BLUE = enum.auto()
    YELLOW = enum.auto()
    MAGENTA = enum.auto()
    CYAN = enum.auto()
    WHITE = enum.auto()
    BLACK = enum.auto()


PARSERS: dict[str, Callable[[str], Any]] = {
    "str": str,
    "path": Path,
    "uuid": UUID,
    "int": int,
    "float": float,
    "hex": HexConstructor(),
    "bool": BoolConstructor(),
    "optional": OptionalConstructor(str),
    "literal": LiteralEvalConstructor(),
    "+literal": LiteralEvalConstructor(plus=True),
}


def interface_interrupt(value: Any) -> int:
    print(f"INTERRUPT:{value=}")
    return 0


MAPPING_INCREMENT = 0


def mapping_increment() -> int:
    global MAPPING_INCREMENT
    MAPPING_INCREMENT += 1
    return MAPPING_INCREMENT


def interface_recipes(
    positional: str,
    stickyPositional: Annotated[
        Sequence[str],
        CliConfig(
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    requiredOption: Annotated[
        str,
        CliConfig(
            flags=("requiredOption",),
        ),
    ],
    defaultOption: str = "",
    overrideFlag: Annotated[
        str,
        CliConfig(
            description="This parameter is defined as `overrideFlag`.",
            flags=("customFlag",),
        ),
    ] = "",
    overrideDefault: Annotated[
        str,
        CliConfig(
            defaultFactory=lambda: "Hello, World!",
        ),
    ] = "",
    flag: Annotated[
        bool,
        CliConfig(
            constructor=FlagConstructor(),
        ),
    ] = False,
    reverseFlag: Annotated[
        bool,
        CliConfig(
            constructor=FlagConstructor(False),
        ),
    ] = True,
    interrupt: Annotated[
        str,
        CliConfig(
            interrupt=interface_interrupt,
        ),
    ] = "",
    interruptTuple: Annotated[
        tuple[str, str],
        CliConfig(
            interrupt=interface_interrupt,
        ),
    ] = ("", ""),
) -> int:
    """Demonstrates various ways to customize the CLI."""
    print(
        f"{positional=}",
        f"{stickyPositional=}",
        f"{requiredOption=}",
        f"{defaultOption=}",
        f"{overrideFlag=}",
        f"{overrideDefault=}",
        f"{flag=}",
        f"{reverseFlag=}",
        f"{interrupt=}",
        f"{interruptTuple=}",
        sep="\n",
    )
    return 0


def simple_types_recipes(
    defaultStr="",
    defaultInt=0,
    typeHintStr: str = "",
    strParam: Annotated[
        str,
        CliConfig(
            aliases=("s",),
        ),
    ] = "",
    pathParam: Annotated[
        Path,
        CliConfig(
            aliases=("p",),
        ),
    ] = Path(),
    intParam: Annotated[
        int,
        CliConfig(
            aliases=("i",),
        ),
    ] = 0,
    uuidParam: Annotated[
        UUID,
        CliConfig(
            aliases=("u",),
        ),
    ] = UUID("00000000-0000-0000-0000-000000000000"),  # noqa: B008 # Immutable
    optionalParam: Annotated[
        str | None,
        CliConfig(
            aliases=("o",),
        ),
    ] = "Not None",
    literalsParam: Annotated[
        Literal["unset", "one", "two", "three"],
        CliConfig(
            aliases=("l",),
        ),
    ] = "unset",
    colorEnumParam: Annotated[
        ColorEnum,
        CliConfig(
            aliases=("c",),
            constructor=ChoicesConstructor.from_enum(ColorEnum, caseSensitive=False),
        ),
    ] = ColorEnum.UNSET,
    flagParam: Annotated[
        int,
        CliConfig(
            aliases=("f",),
            constructor=FlagConstructor(9001),
        ),
    ] = 42,
) -> int:
    """Demonstrates support for built-in types."""
    print(
        f"{defaultStr=}",
        f"{defaultInt=}",
        f"{typeHintStr=}",
        f"{strParam=}",
        f"pathParam={pathParam.as_posix()}",
        f"{intParam=}",
        f"{uuidParam=}",
        f"{optionalParam=}",
        f"{literalsParam=}",
        f"{colorEnumParam=}",
        f"{flagParam=}",
        sep="\n",
    )
    return 0


def complex_types_recipes(
    narrowBoolParam: Annotated[
        bool,
        CliConfig(
            description="Invalid values are rejected.",
            aliases=("n",),
        ),
    ] = False,
    permissiveBoolParam: Annotated[
        bool,
        CliConfig(
            description="Invalid values resolve to `False`.",
            aliases=("b",),
            constructor=BoolConstructor(invalidFinalizer=lambda _: False),
        ),
    ] = False,
    hexParam: Annotated[
        int,
        CliConfig(
            displayType="hex",
            aliases=("x",),
            constructor=HexConstructor(),
        ),
    ] = 0,
    intOrHexParam: Annotated[
        int,
        CliConfig(
            displayType="int | hex",
            aliases=("i",),
            constructor=IntOrHexConstructor(),
        ),
    ] = 0,
    hexStringParam: Annotated[
        str,
        CliConfig(
            displayType="hex",
            aliases=("s",),
            constructor=HexStringConstructor(),
        ),
    ] = "0x0",
    literalParam: Annotated[
        Any,
        CliConfig(
            displayType="Python",
            aliases=("l",),
            constructor=LiteralEvalConstructor(),
        ),
    ] = None,
    plusLiteralParam: Annotated[
        Any,
        CliConfig(
            displayType="str | +Python",
            aliases=("p",),
            constructor=LiteralEvalConstructor(plus=True),
        ),
    ] = None,
    jsonParam: Annotated[
        JsonAlias,
        CliConfig(
            displayType="json",
            aliases=("j",),
            constructor=json.loads,
        ),
    ] = None,
) -> int:
    """Demonstrates support for more complex types."""
    print(
        f"{narrowBoolParam=}",
        f"{permissiveBoolParam=}",
        f"{hexParam=}",
        f"{intOrHexParam=}",
        f"{hexStringParam=}",
        f"{literalParam=}",
        f"{plusLiteralParam=}",
        f"{jsonParam=}",
        sep="\n",
    )
    return 0


def list_recipes(
    sticky: Annotated[
        list[int],
        CliConfig(
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    sticky2: Annotated[
        list[int],
        CliConfig(
            constructor=IterableConstructor(int, list),
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    regular: Annotated[
        list[int] | None,
        CliConfig(
            aliases=("r",),
        ),
    ] = None,
    pairs: Annotated[
        list[tuple[int, int]] | None,
        CliConfig(
            aliases=("p",),
            constructor=IterableConstructor(TupleConstructor(int, int), list),
        ),
    ] = None,
    flags: Annotated[
        list[bool] | None,
        CliConfig(
            aliases=("f",),
            constructor=IterableConstructor(FlagConstructor(), list),
        ),
    ] = None,
    stickyPairs: Annotated[
        list[tuple[int, int]] | None,
        CliConfig(
            aliases=("s",),
            sticky=True,
            stickyStopFlag="--",
        ),
    ] = None,
    single: Annotated[
        list[tuple[int, int]] | None,
        CliConfig(
            description="Not repeatable; the one occurrence becomes a single-item list.",
            repeatable=False,
        ),
    ] = None,
) -> int:
    """Demonstrates various ways to construct lists."""
    print(
        f"{sticky=}",
        f"{sticky2=}",
        f"{regular=}",
        f"{pairs=}",
        f"{flags=}",
        f"{stickyPairs=}",
        f"{single=}",
        sep="\n",
    )
    return 0


def mapping_recipes(
    sticky: Annotated[
        Mapping[str, int],
        CliConfig(
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    sticky2: Annotated[
        Mapping[str, int],
        CliConfig(
            constructor=IterableConstructor(TupleConstructor(str, int), dict),
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    regular: Annotated[
        Mapping[str, int] | None,
        CliConfig(
            aliases=("r",),
        ),
    ] = None,
    pairs: Annotated[
        Mapping[str, tuple[int, int]] | None,
        CliConfig(
            aliases=("p",),
            constructor=IterableConstructor(
                TupleConstructor(str, TupleConstructor(int, int)), dict
            ),
        ),
    ] = None,
    flags: Annotated[
        Mapping[str, bool] | None,
        CliConfig(
            aliases=("f",),
            constructor=IterableConstructor(
                TupleConstructor(
                    CallableConstructor(lambda: str(mapping_increment()), count=0),
                    FlagConstructor(),
                ),
                dict,
            ),
        ),
    ] = None,
    stickyPairs: Annotated[
        Mapping[str, tuple[int, int]] | None,
        CliConfig(
            aliases=("s",),
            sticky=True,
            stickyStopFlag="--",
        ),
    ] = None,
) -> int:
    """Demonstrates various ways to construct mappings."""
    print(
        f"{sticky=}",
        f"{sticky2=}",
        f"{regular=}",
        f"{pairs=}",
        f"{flags=}",
        f"{stickyPairs=}",
        sep="\n",
    )
    return 0


def union_recipes(
    intOrStr: Annotated[
        int | str,
        CliConfig(
            description="Tried in declaration order; `42` is an int, `forty-two` falls back to str.",
            aliases=("i",),
        ),
    ] = 0,
    strOrInt: Annotated[
        str | int,
        CliConfig(
            description="`str` accepts everything, so `int` is never reached.",
            aliases=("s",),
        ),
    ] = 0,
    trailingNone: Annotated[
        int | None,
        CliConfig(
            description="A trailing `None` means `or do nothing`; it is never parsed.",
            aliases=("t",),
        ),
    ] = None,
    leadingNone: Annotated[
        None | int,
        CliConfig(
            description="A leading `None` is parsed first: an empty value is `None`.",
            aliases=("l",),
        ),
    ] = 1,
    intOrBool: Annotated[
        int | bool,
        CliConfig(
            description="Members can be any constructor: `1` is an int, `yes` is a bool.",
            aliases=("b",),
        ),
    ] = 0,
    pairOrPair: Annotated[
        tuple[int, int] | tuple[str, str],
        CliConfig(
            description="Members must consume the same number of values.",
            aliases=("p",),
        ),
    ] = (0, 0),
    floatFirst: Annotated[
        float | Literal["inf", "-inf", "nan"],
        CliConfig(
            description="`float` already parses the special values, so the literals are never reached.",
            aliases=("f",),
        ),
    ] = 0.0,
    specialFirst: Annotated[
        Literal["inf", "-inf", "nan"] | float,
        CliConfig(
            description="The special values are tried first, so they stay strings.",
            aliases=("e",),
        ),
    ] = 0.0,
    numbers: Annotated[
        list[int | Literal["int", "pos", "nat"]] | None,
        CliConfig(
            description=(
                "Each item is a number or the name of a number group. Unions nest anywhere an"
                " annotation does, but `list[int] | Literal[...]` would be rejected: members must"
                " agree on whether they repeat."
            ),
            aliases=("n",),
        ),
    ] = None,
) -> int:
    """Demonstrates unions of arbitrary constructors."""
    print(
        f"{intOrStr=}",
        f"{strOrInt=}",
        f"{trailingNone=}",
        f"{leadingNone=}",
        f"{intOrBool=}",
        f"{pairOrPair=}",
        f"{floatFirst=}",
        f"{specialFirst=}",
        f"{numbers=}",
        sep="\n",
    )
    return 0


class ShoutConstructor(CallableConstructor[[str], str]):
    """Custom constructor that claims `str` annotations and upper-cases the value."""

    @classmethod
    def can_handle(cls, annotation: Any) -> bool:
        return annotation is str

    @classmethod
    def resolve(cls, annotation: Any) -> Generator[Any, Any, "ShoutConstructor"]:
        yield from ()
        return cls(str.upper, displayType="str")


def override_recipes(
    shout: str = "",
    shoutList: list[str] | None = None,
    shoutUnion: int | str = 0,
    number: int = 0,
) -> int:
    """Demonstrates a custom constructor list; every `str` annotation is upper-cased."""
    print(
        f"{shout=}",
        f"{shoutList=}",
        f"{shoutUnion=}",
        f"{number=}",
        sep="\n",
    )
    return 0


def casing_recipes(
    __camelCase: Annotated[  # noqa: PYI063 # For demonstration purposes
        bool,
        CliConfig(
            description="Original: `__camelCase`",
            constructor=FlagConstructor(),
        ),
    ] = False,
    _camelCase: Annotated[
        bool,
        CliConfig(
            description="Original: `_camelCase`",
            constructor=FlagConstructor(),
        ),
    ] = False,
    camelCase: Annotated[
        bool,
        CliConfig(
            description="Original: `camelCase`",
            constructor=FlagConstructor(),
        ),
    ] = False,
    snake_case: Annotated[
        bool,
        CliConfig(
            description="Original: `snake_case`",
            constructor=FlagConstructor(),
        ),
    ] = False,
    UPPER_SNAKE_CASE: Annotated[
        bool,
        CliConfig(
            description="Original: `UPPER_SNAKE_CASE`",
            constructor=FlagConstructor(),
        ),
    ] = False,
    PascalCase: Annotated[
        bool,
        CliConfig(
            description="Original: `PascalCase`",
            constructor=FlagConstructor(),
        ),
    ] = False,
) -> int:
    """Demonstrates supported casing modes."""
    print(
        f"{__camelCase=}",
        f"{_camelCase=}",
        f"{camelCase=}",
        f"{snake_case=}",
        f"{UPPER_SNAKE_CASE=}",
        f"{PascalCase=}",
        sep="\n",
    )
    return 0


def parse_cli(
    format: Annotated[
        Literal[
            "str", "path", "uuid", "int", "float", "hex", "bool", "optional", "literal", "+literal"
        ],
        CliConfig(
            description="The format to parse the value in.",
        ),
    ],
    value: Annotated[
        str,
        CliConfig(
            description="The value to parse.",
        ),
    ],
) -> int:
    """Parses a value of the selected type."""
    try:
        parsed = PARSERS[format](value)
    except Exception as e:  # noqa: BLE001 # Intentional catch-all
        print(f"Error: {e}")
        return 1
    print(
        f"{format=}",
        f"{value=}",
        f"{parsed=}",
        sep="\n",
    )
    return 0


cli = Subcommand(
    {
        ("parse", "p"): Cli(parse_cli),
        ("casing", "c"): Subcommand(
            {
                ("insensitive", "i"): Subcommand(
                    {
                        ("kebab", "k"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to kebab-case.",
                            caseSensitive=False,
                            flagCase=CaseType.KEBAB,
                        ),
                        ("upper-kebab", "K"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to UPPER-KEBAB-CASE.",
                            caseSensitive=False,
                            flagCase=CaseType.KEBAB_UPPER,
                        ),
                        ("snake", "s"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to snake_case.",
                            caseSensitive=False,
                            flagCase=CaseType.SNAKE,
                        ),
                        ("upper-snake", "S"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to UPPER_SNAKE_CASE.",
                            caseSensitive=False,
                            flagCase=CaseType.SNAKE_UPPER,
                        ),
                        ("camel", "c"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to camelCase.",
                            caseSensitive=False,
                            flagCase=CaseType.CAMEL,
                        ),
                        ("pascal", "p"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to PascalCase.",
                            caseSensitive=False,
                            flagCase=CaseType.PASCAL,
                        ),
                    },
                    description="Explore casing options in case-insensitive mode.",
                    helpCommands=("?",),
                ),
                ("sensitive", "s"): Subcommand(
                    {
                        ("kebab", "k"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to kebab-case.",
                            flagCase=CaseType.KEBAB,
                        ),
                        ("upper-kebab", "K"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to UPPER-KEBAB-CASE.",
                            flagCase=CaseType.KEBAB_UPPER,
                        ),
                        ("snake", "s"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to snake_case.",
                            flagCase=CaseType.SNAKE,
                        ),
                        ("upper-snake", "S"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to UPPER_SNAKE_CASE.",
                            flagCase=CaseType.SNAKE_UPPER,
                        ),
                        ("camel", "c"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to camelCase.",
                            flagCase=CaseType.CAMEL,
                        ),
                        ("pascal", "p"): Cli(
                            casing_recipes,
                            description="Demonstrates how various casing gets converted to PascalCase.",
                            flagCase=CaseType.PASCAL,
                        ),
                    },
                    description="Explore casing options in case-sensitive mode.",
                    helpCommands=("?",),
                ),
            },
            description="Demonstrates casing options for flags.",
            helpCommands=("?",),
        ),
        ("recipes", "r"): Subcommand(
            {
                ("interfaces", "i"): Cli(interface_recipes),
                ("types", "t"): Cli(simple_types_recipes),
                ("constructors", "c"): Cli(complex_types_recipes),
                ("lists", "l"): Cli(list_recipes),
                ("mappings", "m"): Cli(mapping_recipes),
                ("unions", "u"): Cli(union_recipes),
                ("overrides", "o"): Cli(
                    override_recipes,
                    constructors=[ShoutConstructor, *DEFAULT_CONSTRUCTORS],
                ),
                ("windows", "w"): Subcommand(
                    {
                        ("interfaces", "i"): Cli(
                            interface_recipes,
                            flagCase=CaseType.SNAKE_UPPER,
                            flagPrefixes=("/", "/"),
                        ),
                        ("types", "t"): Cli(
                            simple_types_recipes,
                            flagCase=CaseType.SNAKE_UPPER,
                            flagPrefixes=("/", "/"),
                        ),
                        ("constructors", "c"): Cli(
                            complex_types_recipes,
                            flagCase=CaseType.SNAKE_UPPER,
                            flagPrefixes=("/", "/"),
                        ),
                        ("lists", "l"): Cli(
                            list_recipes,
                            flagCase=CaseType.SNAKE_UPPER,
                            flagPrefixes=("/", "/"),
                        ),
                        ("mappings", "m"): Cli(
                            mapping_recipes,
                            flagCase=CaseType.SNAKE_UPPER,
                            flagPrefixes=("/", "/"),
                        ),
                        ("unions", "u"): Cli(
                            union_recipes,
                            flagCase=CaseType.SNAKE_UPPER,
                            flagPrefixes=("/", "/"),
                        ),
                        ("overrides", "o"): Cli(
                            override_recipes,
                            constructors=[ShoutConstructor, *DEFAULT_CONSTRUCTORS],
                            flagCase=CaseType.SNAKE_UPPER,
                            flagPrefixes=("/", "/"),
                        ),
                    },
                    description="Various CLI definition recipe books with Windows-style args.",
                    helpCommands=("?",),
                ),
            },
            description="Various CLI definition recipe books for demonstration purposes.",
            helpCommands=("?",),
        ),
    },
    helpCommands=("?",),
)


if __name__ == "__main__":
    cli.main()
