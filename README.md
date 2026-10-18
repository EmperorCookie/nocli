# nocli

Function signature driven CLI authoring for Python.

Turn ordinary Python functions into fully featured CLIs without maintaining a separate parser definition. `nocli` derives CLI behavior from function signatures and type annotations, with `Annotated` configuration and composable constructors for explicit customization.

## Why nocli?

I'm not claiming `nocli` is better than `Typer`/`Cyclopts`/`Click`, but it's the accumulation of small design decision by those libraries that made me want to build my own. I want the CLI to be built around my program, not the other way around.

- **Prioritize collocation**: CLI configuration and documentation are collocated with the function parameters they describe through `Annotated` and `CliConfig`.
- **Prefer declarative interfaces**: `nocli` derives the CLI from function signatures and metadata rather than requiring an imperative parser definition.
- **Compose small components**: Complex parsing behavior is built by composing generic constructors such as `UnionConstructor`, `TupleConstructor`, and `IterableConstructor`; `Subcommand` is just a carefully configured `Cli`.
- **Make the common case boring**: Ordinary Python functions with standard type annotations require little or no CLI-specific configuration.
- **Leverage Python's type system**: Standard annotations such as `list[int]`, `tuple[str, int]`, `Literal[...]`, enums, and unions directly determine CLI parsing behavior.
- **Accommodate fringe behavior**: Custom constructors and configuration overrides allow behavior outside the library's built-in inference without requiring changes to the underlying CLI model.
- **Separate aesthetics from mechanics**: User-facing presentation such as flag casing, prefixes, aliases, and displayed types is configurable independently of parsing behavior.
- **Fail loudly**: Unsupported annotations, invalid configurations, and unhandled parsing cases produce explicit errors instead of silently falling back to potentially incorrect behavior.
- **Design for discoverability**: The CLI's behavior, configuration, and documentation can be understood directly from the function signature and its collocated metadata.

So why `nocli`? Because it gets out of the way when you aren't using it.

## Features

An unchecked box indicates a feature has yet to be implemented.

Note: I'm the sole maintainer of this library; I prioritize the features that I need and use. If you want a feature prioritized (whether it's in the list below or not), please open an issue and make the request.

### CLI

- ✅ Positional arguments
- ✅ Options and aliases
- ✅ Parameter descriptions via `Annotated`
- ✅ Custom aliases via `CliConfig`
- ✅ Case-sensitive and case-insensitive flag matching
- ✅ Boolean flags (`FlagConstructor`)
- ✅ Repeatable arguments
- ✅ Sticky arguments
- ✅ Subcommand routing
- 🚧 Subcommand-level options

### Parser

- ✅ Automatic parsing from basic type annotations
- ✅ Custom constructors support
    - ✅ Custom constructors chosen by type annotation (`Cli(constructors=...)`)
- ✅ Hex (int/str, mixed int/hex)
- ✅ Boolean values (strict by default)
    - ✅ Automatically detected
- ✅ Unions (`X | Y`, `Union[...]`), tried in declaration order
    - ✅ Automatically detected
- ✅ `X | None` (the option is simply absent) and `None | X` (an empty value is `None`)
    - ✅ Automatically detected
    - ✅ `OptionalConstructor` for custom `None` values
- ✅ Tuple types
    - ✅ Automatically detected
- ✅ Iterable types
    - ✅ Automatically detected
- ✅ Mapping types
    - ✅ Automatically detected
- ✅ `Literal[...]`
    - ✅ Automatically detected
- ✅ Enums
    - ✅ Automatically detected
- 🚧 Unions of values that consume a different number of CLI values
- 🚧 Structured types such as `NamedTuple` and dataclasses

## Installation

Install using pip:

```bash
pip install nocli
```

## Usage

Full example: [example.py](example.py)

The simple example below shows how to create a CLI from a regular Python function:

```python
#!/bin/python3
from typing import Annotated

from nocli import Cli, CliConfig

def greet(
    name: str,
    # Description and metaconfig is collocated
    greeting: Annotated[str, CliConfig(description="The greeting to use.")] = "Hello"
) -> int:
    """Greet someone with a custom greeting."""
    print(f"{greeting}, {name}!")
    return 0

cli = Cli(greet)

if __name__ == "__main__":
    cli.main()
```

This creates the following CLI:

```text
$ python greet.py -h
Greet someone with a custom greeting.

Positionals:
  [name <str> (required)]

Options (case-sensitive):
  --greeting <str> (default: 'Hello')
    The greeting to use.
  -h | --help (flag, default: False)
    Shows this help message.

$ python greet.py "World" --greeting "Sup"
Sup, World!
```

### Type hints

Standard type hints are all it takes for most parameters. Unions are tried in the order they are declared, collections can be repeated, and tuples take a fixed number of values:

```python
#!/bin/python3
from typing import Literal

from nocli import Cli

def resize(
    path: str,
    # Unions are tried in order: `42` is an int, `auto` is the literal
    width: int | Literal["auto"] = "auto",
    # Collections can be repeated, and tuples take a fixed number of values
    tags: list[str] | None = None,
    size: tuple[int, int] = (80, 24),
) -> int:
    """Resizes an image."""
    print(f"{path=} {width=} {tags=} {size=}")
    return 0

cli = Cli(resize)

if __name__ == "__main__":
    cli.main()
```

The help describes how each value is parsed:

```text
$ python resize.py -h
Resizes an image.

Positionals:
  [path <str> (required)]

Options (case-sensitive):
  --width <int | 'auto'> (default: 'auto')
  --tags <list[str]> (repeatable, default: None)
  --size <(int, int)> (default: (80, 24))
  -h | --help (flag, default: False)
    Shows this help message.

$ python resize.py cat.png --width 42 --tags a --tags b --size 800 600
path='cat.png' width=42 tags=['a', 'b'] size=(800, 600)
```

Some notes on how type hints are interpreted:

- A trailing `None` (`int | None`) means "or do nothing": the option is simply absent, so there is never anything to parse. A leading `None` (`None | int`) is parsed first, and treats an empty value as `None`.
- All members of a union must consume the same number of CLI values; otherwise, building the `Cli` raises an error instead of guessing.
- Annotations that no constructor handles raise an error when the `Cli` is built, rather than falling back to something that might be wrong.

### Constructors

Constructors control how raw CLI values are converted before being passed to your function. They can be supplied through `CliConfig` and composed to build more complex conversions.

```python
#!/bin/python3
from typing import Annotated

from nocli import Cli, CliConfig
from nocli.constructors import BoolConstructor

# Booleans are strict by default: only recognized values (and numbers) are accepted, and
# anything else is a parse error. `invalidFinalizer` opts into the permissive behavior; here,
# unrecognized values simply resolve to `False`.
def truthy(
    value: Annotated[
        bool, CliConfig(constructor=BoolConstructor(invalidFinalizer=lambda _: False))
    ],
) -> int:
    """Parses common truthy representations; other values are `False`."""
    print(value)
    return 0

cli = Cli(truthy)

if __name__ == "__main__":
    cli.main()
```

Which results in:

```text
$ python truthy.py -h
Parses common truthy representations; other values are `False`.

Positionals:
  [value <bool> (required)]

Options (case-sensitive):
  -h | --help (flag, default: False)
    Shows this help message.

$ python truthy.py 1
True

$ python truthy.py true
True

$ python truthy.py yes
True

$ python truthy.py purple
False
```

#### Custom constructors for type hints

Each constructor decides for itself which type hints it handles, and `Cli` asks them in order until one does. The defaults are in `nocli.DEFAULT_CONSTRUCTORS`. To change how a type hint is handled, build your own list and pass it to `Cli`; it replaces the defaults entirely, so include them where you still want them:

```python
#!/bin/python3
from collections.abc import Generator
from typing import Any

from nocli import DEFAULT_CONSTRUCTORS, Cli
from nocli.constructors import CallableConstructor, ConstructorAbc

class ShoutConstructor(CallableConstructor[[str], str]):
    """Handles `str` annotations by upper-casing the value."""

    @classmethod
    def can_handle(cls, annotation: Any) -> bool:
        return annotation is str

    @classmethod
    def resolve(cls, annotation: Any) -> Generator[Any, ConstructorAbc, ConstructorAbc]:
        yield from ()  # Nothing nested to resolve
        return cls(str.upper, displayType="str")

def hello(name: str, times: list[str] | None = None) -> int:
    print(name, times)
    return 0

# Constructors are asked in order, and the first one that handles the annotation is used
cli = Cli(hello, constructors=[ShoutConstructor, *DEFAULT_CONSTRUCTORS])

if __name__ == "__main__":
    cli.main()
```

Nested type hints are resolved with the same list, so `list[str]` upper-cases each item too:

```text
$ python shout.py world --times a --times b
WORLD ['A', 'B']
```

#### Composing constructors by hand

The constructors that handle type hints apply to type hints. A constructor that you compose yourself uses what you give it as it is, so a plain `bool` is the builtin `bool`, not a `BoolConstructor`:

```python
from nocli import DEFAULT_CONSTRUCTORS
from nocli.constructors import ConstructorAbc, IterableConstructor

literal = IterableConstructor(bool, list)
derived = IterableConstructor(ConstructorAbc.from_annotation(bool, *DEFAULT_CONSTRUCTORS), list)

print(literal(["false", "yes"]))  # [True, True]: the builtin `bool("false")` is `True`
print(derived(["false", "yes"]))  # [False, True]: the handler for `bool` parses the words
```

`ConstructorAbc.from_annotation` derives a constructor from a type hint using the constructors you pass it, so give it the same list you gave to `Cli` for the same results. The same goes for the elements of `TupleConstructor` and the members of `UnionConstructor`.

### Subcommand Router

`Subcommand` groups multiple CLIs into a command hierarchy. Each subcommand can be a `Cli` or another `Subcommand`.

```python
#!/bin/python3
from nocli import Subcommand

from .greet import cli as greet_cli
from .truthy import cli as truthy_cli

cli = Subcommand({
    # Supports both strings and tuples for command aliases
    "greet": greet_cli,
    ("truthy", "t"): truthy_cli,
})

if __name__ == "__main__":
    cli.main()
```

And its resulting CLI:

```text
$ python subcommand.py help
Runs a subcommand from the list of options below.

Positionals:
  [subcommand (required)]
    greet:
      Greet someone with a custom greeting.
    t | truthy:
      Parses common truthy representations; other values are `False`.
    help:
      Shows the help for this application or its subcommand(s).
  [args... (repeatable, sticky)]

$ python subcommand.py greet King
Hello, King!
```
