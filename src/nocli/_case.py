import enum
import re


class CaseType(enum.Enum):
    """Casing conventions that flag names can be converted to."""

    KEBAB = enum.auto()
    KEBAB_UPPER = enum.auto()
    SNAKE = enum.auto()
    SNAKE_UPPER = enum.auto()
    CAMEL = enum.auto()
    PASCAL = enum.auto()

    def convert(self, value: str, filler: str = "") -> str:
        """
        Converts the case of the value to the target case type.

        Args:
            value:
                The name to convert, in any of the supported casings.
            filler:
                The text that replaces each leading separator (e.g. `_` in `_name`), so that the
                prefix survives the conversion.

        Returns:
            The value in the target case type.

        Raises:
            ValueError:
                `value` has no words to convert.
        """
        # Split on kebab, snake, and camelCase/PascalCase word boundaries
        words = list(re.split(r"[-_]|(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", value))
        prefix = ""
        while words and words[0] == "":
            del words[0]
            prefix += filler
        if len(words) == 0:
            raise ValueError(f"Expected at least one word; got `{value}`")
        if self == CaseType.KEBAB:
            return prefix + "-".join(words).lower()
        if self == CaseType.KEBAB_UPPER:
            return prefix + "-".join(words).upper()
        if self == CaseType.SNAKE:
            return prefix + "_".join(words).lower()
        if self == CaseType.SNAKE_UPPER:
            return prefix + "_".join(words).upper()
        if self == CaseType.CAMEL:
            return prefix + words[0].lower() + "".join(w.capitalize() for w in words[1:])
        if self == CaseType.PASCAL:
            return prefix + "".join(w.capitalize() for w in words)
        raise ValueError(f"Expected a known case type; got `{self}`")
