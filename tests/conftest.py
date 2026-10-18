import pytest


@pytest.fixture
def usage(capsys):
    """Returns a function that gives the full help text of a `Cli`, as the user would see it."""

    def get(cli):
        assert cli.run(["-h"]) == 0
        return capsys.readouterr().err

    return get
