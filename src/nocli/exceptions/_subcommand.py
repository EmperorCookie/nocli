from ._base import CliBuildError


class DuplicateCommandError(CliBuildError):
    """Two or more commands are trying to use the same name."""

    def __init__(self, name: str) -> None:
        """
        Args:
            name:
                Name of the command that already exists.
        """
        self._name = name
        super().__init__(
            f"Expected an unregistered command name; got duplicate command `{self.name}`"
        )

    @property
    def name(self) -> str:
        """The name that is already in use."""
        return self._name
