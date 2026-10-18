import dataclasses as dc
from collections.abc import Callable, Sequence
from typing import Any

from .constructors import ConstructorAbc


@dc.dataclass(kw_only=True)
class CliConfig:
    """
    Metadata for a CLI parameter, attached via `Annotated`. All attributes are treated as
    overrides. Any attribute set here supersedes the default behavior unless specified otherwise.

    Attributes:
        description:
            Help string shown in built-in help output for this parameter.
        displayName:
            Overrides the primary flag name derived from the Python parameter name. Affects
            both the actual flag used at the CLI and the name shown in help output. Must contain
            at least one word; an empty name is an error.
        displayType:
            Overrides the type or value label shown in help output, e.g. `--output <FILE>` instead
            of `--output <Path>`. By default it is how the constructor describes itself, such as
            `list[int]` or `'a' | 'b'`.

            An empty string omits the type from the help output.
        displayDefault:
            Overrides the default value shown in help output, which is otherwise the result of
            `defaultFactory` if set, or the Python default. Shown verbatim; when set,
            `defaultFactory` is not called for display purposes.

            An empty string omits the default from the help output, like `displayType`. To show
            an empty string default, quote it: `'""'`.
        flags:
            If `None`, inferred from the Python signature: parameters without a default become
            positionals; parameters with a default become flags named after the parameter. If an
            explicit sequence, those exact flags are used and the parameter is unconditionally
            treated as a flag option.
        aliases:
            Alternative flag names that also set this parameter.
        constructor:
            Overrides the constructor derived from the type annotation, which `Cli` otherwise
            derives using its `constructors`.
            For non-repeatable options: called on the collected token string(s) immediately.
            For repeatable options: a finalizer called once on the complete list of accumulated
            raw tokens after all argv has been consumed. With `count=1` the list contains
            plain strings; with `count>1` it contains tuples of strings.

            A `ConstructorAbc` owns its `count` and `repeatable` behavior, so `count` and
            `repeatable` below only apply to a plain callable. A plain callable is described in
            help by its name; use `displayType` to change that.
        defaultFactory:
            A zero-argument callable that produces the value to use when this option is
            absent from the command line. Setting this makes the option optional regardless of
            whether the Python parameter has a default, and decouples the CLI fallback from the
            function signature (useful for dynamic defaults such as environment variables).

            Note that this gets called during help generation to get a default value for display
            purposes, unless `displayDefault` is set.
        count:
            Overrides the number of CLI values consumed per invocation. Only applies to a plain
            callable constructor; setting it alongside a `ConstructorAbc` is an error, since the
            constructor already knows how many values it consumes.
            For `repeatable` options, this attribute dictates the number of CLI values required
            for one element to be added to the list.

            If set to 0, the option is treated as a "flag only" option; no value will be
            consumed from the CLI when the user passes this option, and the constructor will be
            called without any arguments. The constructor is never called if the flag isn't
            passed by the user. `FlagConstructor` is the ready-made constructor for this. A
            `repeatable` option is the exception: its constructor is given the list of its
            occurrences, each of which is an empty tuple.

            Must be ≥0.

            Variable-length consumption is not supported. To accept a variable number of
            values in a single invocation, use `count=1` and pass the values as a Python
            literal (e.g. `+[1, 2, 3]`) using `LiteralEvalConstructor(plus=True)`, then validate
            the resulting shape.
        repeatable:
            If `True`, this option can be called multiple times. Raw tokens are accumulated
            into a list and passed to the constructor as a single finalizer call after parsing
            completes. If `count` is greater than 1, each invocation contributes a tuple of
            strings to the list rather than a plain string.

            A `ConstructorAbc` decides this itself, so for one only `False` has an effect: it
            disables the repeatable nature of the constructor, so the option can be given once
            and yields a single-item collection.
        sticky:
            If `True`, the option consumes every subsequent token as a value, including tokens
            that look like other flags, until argv is exhausted or a `stickyStopFlag` is
            encountered.
        stickyStopFlag:
            If set, this flag can be used by the user to stop a sticky option from consuming
            tokens.
        interrupt:
            If set, this callable will be invoked with the constructed value as its argument as
            soon as the flag is matched, interrupting parsing immediately.

            For repeatable options, this is called the first time the option is encountered.
    """

    description: str | None = dc.field(default=None)
    displayName: str | None = dc.field(default=None)
    displayType: str | None = dc.field(default=None)
    displayDefault: str | None = dc.field(default=None)
    flags: Sequence[str] | None = dc.field(default=None)
    aliases: Sequence[str] | None = dc.field(default=None)
    constructor: ConstructorAbc[..., Any] | Callable[..., Any] | None = dc.field(default=None)
    defaultFactory: Callable[[], Any] | None = dc.field(default=None)
    count: int | None = dc.field(default=None)
    repeatable: bool | None = dc.field(default=None)
    sticky: bool | None = dc.field(default=None)
    stickyStopFlag: str | None = dc.field(default=None)
    interrupt: Callable[[Any], int] | None = dc.field(default=None)
