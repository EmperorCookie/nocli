from .constructors import (
    BoolConstructor,
    CallableConstructor,
    ChoicesConstructor,
    ConstructorAbc,
    IterableConstructor,
    NoneConstructor,
    TupleConstructor,
    UnionConstructor,
)

# Maintainers: deliberately mutable, so users may change the default for every `Cli`. Treat as
# fully malleable: snapshot where consumed (as `Cli` and `CliParamSpec` do), never assume any entry
# is present or at which position, and give the parameters declared by the library an explicit
# `CliConfig(constructor=...)` rather than relying on annotations resolving
DEFAULT_CONSTRUCTORS: list[type[ConstructorAbc]] = [
    # Composite constructors
    TupleConstructor,
    IterableConstructor,
    UnionConstructor,
    # Simple constructors
    BoolConstructor,
    ChoicesConstructor,
    NoneConstructor,
    # Catch-all, as any plain callable is a constructor; must stay last
    CallableConstructor,
]
"""
The constructors `Cli` uses by default to derive a constructor from a type annotation.

Each is asked in order, so the ones ahead in the list are evaluated first, and the first one that
handles the annotation is used. To customize the behavior, build a separate list and pass it as
`Cli(constructors=...)`; an override replaces this list entirely, it is not merged with it.
"""
