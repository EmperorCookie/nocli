import nocli


def _make_subcommand(**kwargs):
    def foo(value: str) -> int:
        return len(value)

    def bar(value: str) -> int:
        return int(value)

    return nocli.Subcommand({"foo": nocli.Cli(foo), "bar": nocli.Cli(bar)}, **kwargs)


def test_routes_to_correct_subcommand():
    cli = _make_subcommand()
    assert cli.run(["foo", "x" * 42]) == 42
    assert cli.run(["bar", "42"]) == 42


def test_unknown_subcommand_returns_nonzero():
    cli = _make_subcommand()
    assert cli.run(["baz", "x"]) == 2


def test_no_args_returns_nonzero():
    cli = _make_subcommand()
    assert cli.run([]) != 0


def test_description_set():
    def fn() -> int:
        return 0

    cli = nocli.Subcommand({"fn": nocli.Cli(fn)}, description="A description.")
    assert cli.description == "A description."


def test_no_description_has_default():
    def fn() -> int:
        return 0

    assert nocli.Subcommand({"fn": nocli.Cli(fn)}).description is not None


def test_case_insensitive_subcommand_name():
    cli = _make_subcommand(caseSensitive=False)
    assert cli.run(["FOO", "bar"]) == 3


def test_case_sensitive_by_default():
    cli = _make_subcommand()
    assert cli.run(["FOO", "x"]) == 2


def test_nested_subcommands():
    def leaf(value: str) -> int:
        return len(value)

    inner = nocli.Subcommand({"leaf": nocli.Cli(leaf)})
    outer = nocli.Subcommand({"inner": inner})
    assert outer.run(["inner", "leaf", "x" * 42]) == 42


def test_subcommand_is_cli():
    cli = _make_subcommand()
    assert isinstance(cli, nocli.Cli)
