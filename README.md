# nocli

Function signature driven CLI authoring for Python.

Turn ordinary Python functions into fully featured CLIs without maintaining a separate parser definition. `nocli` derives CLI behavior from function signatures and type annotations, with `Annotated` configuration and composable constructors for explicit customization.

## Why nocli?

I'm not claiming `nocli` is better than `Typer`/`Cyclopts`/`Click`, but it's the accumulation of small design decision by those libraries that made me want to build my own. I want the CLI to be built around my program, not the other way around.

- **Prioritize collocation**: CLI configuration and documentation are collocated with the function parameters they describe through `Annotated` and `CliConfig`.
- **Prefer declarative interfaces**: `nocli` derives the CLI from function signatures and metadata rather than requiring an imperative parser definition.
- **Compose small components**: Complex parsing behavior is built by composing generic constructors such as `OptionalConstructor`, `TupleConstructor`, and `IterableConstructor`; `Subcommand` is just a carefully configured `Cli`.
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

- [x] Positional arguments
- [x] Options and aliases
- [x] Parameter descriptions via `Annotated`
- [x] Custom aliases via `CliConfig`
- [x] Case-sensitive and case-insensitive flag matching
- [x] Boolean flags
- [x] Repeatable arguments
- [x] Sticky arguments
- [x] Subcommand routing
- [ ] Subcommand-level options

### Parser

- [x] Automatic parsing from basic type annotations
- [x] Custom constructors support
- [x] Hex (int/str, mixed int/hex)
- [x] Boolean values (strict by default)
    - [x] Automatically detected
- [x] `Optional` and `X | None`
    - [x] Automatically detected
- [x] Tuple types
    - [ ] Automatically detected
- [x] Iterable types
    - [ ] Automatically detected
- [x] Mapping types
    - [ ] Automatically detected
- [x] `Literal[...]`
    - [x] Automatically detected
- [x] Enums
    - [x] Automatically detected
- [ ] `Union[...]` (beyond `| None`)
    - [ ] Automatically detected

## Installation

Install using pip:

```bash
pip install nocli
```

## Usage

Full example: [example.py](example.py)

Th simple example below shows how to create a CLI from a regular Python function:

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

### Constructors

Constructors control how raw CLI values are converted before being passed to your function. They can be supplied through `CliConfig` and composed to build more complex conversions.

```python
#!/bin/python3
from typing import Annotated

from nocli import Cli, CliConfig
from nocli.constructors import BoolConstructor

# Booleans are strict by default: only recognized values (and numbers) are accepted, and
# anything else is a parse error. `invalid=False` opts into the permissive behavior where
# unrecognized values simply resolve to `False`.
def truthy(
    value: Annotated[bool, CliConfig(constructor=BoolConstructor(invalid=False))],
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
  [subcommand <str> (required)]
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
