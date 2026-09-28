"""Example CLI. Run with: `python example.py`"""

import enum
import json
from collections.abc import Callable, Mapping, Sequence
from operator import not_
from pathlib import Path
from types import NoneType
from typing import Annotated, Any, Literal
from uuid import UUID

from nocli import CaseType, Cli, CliConfig, Subcommand
from nocli.constructors import (
    BoolConstructor,
    ChoicesConstructor,
    HexConstructor,
    IntOrHexConstructor,
    HexStringConstructor,
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
            displayType="list[str]",
            repeatable=True,
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
            count=0,
        ),
    ] = False,
    reverseFlag: Annotated[
        bool,
        CliConfig(
            constructor=not_,
            count=0,
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
            count=2,
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
    ] = UUID("00000000-0000-0000-0000-000000000000"),
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
            constructor=lambda: 9001,
            count=0,
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
            constructor=BoolConstructor(invalid=False),
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
            constructor=IterableConstructor(list, int),
            repeatable=True,
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    sticky2: Annotated[
        list[int],
        CliConfig(
            constructor=IterableConstructor(list, int),
            repeatable=True,
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    regular: Annotated[
        list[int] | None,
        CliConfig(
            aliases=("r",),
            constructor=IterableConstructor(list, int),
            repeatable=True,
        ),
    ] = None,
    pairs: Annotated[
        list[tuple[int, int]] | None,
        CliConfig(
            aliases=("p",),
            constructor=IterableConstructor(list, TupleConstructor(int, int)),
            count=2,
            repeatable=True,
        ),
    ] = None,
    flags: Annotated[
        list[bool] | None,
        CliConfig(
            aliases=("f",),
            constructor=IterableConstructor(list, bool),
            count=0,
            repeatable=True,
        ),
    ] = None,
    stickyPairs: Annotated[
        list[tuple[int, int]] | None,
        CliConfig(
            aliases=("s",),
            constructor=IterableConstructor(list, TupleConstructor(int, int)),
            count=2,
            repeatable=True,
            sticky=True,
            stickyStopFlag="--",
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
        sep="\n",
    )
    return 0


def mapping_recipes(
    sticky: Annotated[
        Mapping[str, int],
        CliConfig(
            constructor=IterableConstructor(dict, TupleConstructor(str, int)),
            count=2,
            repeatable=True,
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    sticky2: Annotated[
        Mapping[str, int],
        CliConfig(
            constructor=IterableConstructor(dict, TupleConstructor(str, int)),
            count=2,
            repeatable=True,
            sticky=True,
            stickyStopFlag="--",
        ),
    ],
    regular: Annotated[
        Mapping[str, int] | None,
        CliConfig(
            aliases=("r",),
            constructor=IterableConstructor(dict, TupleConstructor(str, int)),
            count=2,
            repeatable=True,
        ),
    ] = None,
    pairs: Annotated[
        Mapping[str, tuple[int, int]] | None,
        CliConfig(
            aliases=("p",),
            constructor=IterableConstructor(
                dict, TupleConstructor(str, TupleConstructor(int, int))
            ),
            count=3,
            repeatable=True,
        ),
    ] = None,
    flags: Annotated[
        Mapping[str, bool] | None,
        CliConfig(
            aliases=("f",),
            constructor=IterableConstructor(
                dict, TupleConstructor(lambda _: str(mapping_increment()), lambda _: True)
            ),
            count=0,
            repeatable=True,
        ),
    ] = None,
    stickyPairs: Annotated[
        Mapping[str, tuple[int, int]] | None,
        CliConfig(
            aliases=("s",),
            constructor=IterableConstructor(
                dict, TupleConstructor(str, TupleConstructor(int, int))
            ),
            count=3,
            repeatable=True,
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


def casing_recipes(
    __camelCase: Annotated[
        bool,
        CliConfig(
            description="Original: `__camelCase`",
            count=0,
        ),
    ] = False,
    _camelCase: Annotated[
        bool,
        CliConfig(
            description="Original: `_camelCase`",
            count=0,
        ),
    ] = False,
    camelCase: Annotated[
        bool,
        CliConfig(
            description="Original: `camelCase`",
            count=0,
        ),
    ] = False,
    snake_case: Annotated[
        bool,
        CliConfig(
            description="Original: `snake_case`",
            count=0,
        ),
    ] = False,
    UPPER_SNAKE_CASE: Annotated[
        bool,
        CliConfig(
            description="Original: `UPPER_SNAKE_CASE`",
            count=0,
        ),
    ] = False,
    PascalCase: Annotated[
        bool,
        CliConfig(
            description="Original: `PascalCase`",
            count=0,
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
    except Exception as e:
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
