class NocliError(Exception):
    def __init__(self, message: str) -> None:
        self._message = message

    @property
    def message(self) -> str:
        """A human readable error message."""
        return self._message


class CliBuildError(NocliError): ...


class ParserError(NocliError): ...
