from typing import Annotated

import nocli


def test_config_description_in_help():
    def fn(name: Annotated[str, nocli.CliConfig(description="Your name.")]) -> int:
        return len(name)

    assert "Your name." in nocli.Cli(fn)._format_help(full=True)


def test_config_description_keyword_in_help():
    def fn(*, count: Annotated[int, nocli.CliConfig(description="How many times.")] = 1):
        return count

    assert "How many times." in nocli.Cli(fn)._format_help(full=True)


def test_config_no_description_omitted_from_help():
    def fn(name: str) -> int:
        return len(name)

    help_text = nocli.Cli(fn)._format_help(full=True)
    assert "name" in help_text
    assert "Your name." not in help_text


def test_config_does_not_affect_value():
    def fn(*, count: Annotated[int, nocli.CliConfig(description="How many.")] = 1):
        return count

    assert nocli.Cli(fn).run(["--count", "5"]) == 5


def test_config_without_description_is_valid():
    def fn(*, count: Annotated[int, nocli.CliConfig()] = 1):
        return count

    assert nocli.Cli(fn).run(["--count", "3"]) == 3


def test_config_sticky_stop_flag_stops_consumption():
    captured = []

    def fn(
        files: Annotated[
            list[str],
            nocli.CliConfig(repeatable=True, sticky=True, stickyStopFlag="--"),
        ] = [],
        out: str = "",
    ) -> int:
        captured.append({"files": files, "out": out})
        return 0

    nocli.Cli(fn).run(["--files", "a", "b", "--", "--out", "result"])
    assert captured[-1] == {"files": ["a", "b"], "out": "result"}


def test_config_sticky_without_stop_flag_never_stops():
    def fn(
        files: Annotated[
            list[str], nocli.CliConfig(repeatable=True, sticky=True)
        ] = [],
    ) -> int:
        return len(files)

    # No `stickyStopFlag`, so the stop token is just another value
    assert nocli.Cli(fn).run(["--files", "a", "b", "--"]) == 3


def test_config_sticky_stop_flag_shown_in_help():
    def fn(
        files: Annotated[
            list[str],
            nocli.CliConfig(repeatable=True, sticky=True, stickyStopFlag="--"),
        ] = [],
    ) -> int:
        return len(files)

    help_text = nocli.Cli(fn)._format_help(full=True)
    assert "sticky[stop=`--`]" in help_text
