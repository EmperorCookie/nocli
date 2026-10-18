class NocliError(Exception):
    """Base class of every error that `nocli` raises on purpose."""

    def __init__(self, message: str) -> None:
        """
        Args:
            message:
                A human readable description of the error.
        """
        super().__init__(message)
        self._message = message

    @property
    def message(self) -> str:
        """A human readable error message."""
        return self._message


class CliBuildError(NocliError):
    """A CLI is defined in a way that `nocli` is unable to build, before anything is parsed."""


class ParserError(NocliError):
    """The user's arguments are unable to be parsed."""
