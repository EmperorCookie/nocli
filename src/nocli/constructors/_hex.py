from collections.abc import Iterable
from typing import Any, Literal

from .._compat import Self
from ._callable import CallableConstructor


class HexStringConstructor(CallableConstructor[[str], str]):
    """Normalizes hex strings."""

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return False  # There are no builtin types that resolve to a hex

    def __init__(
        self,
        outputPrefix: str = "0x",
        *,
        validPrefixes: Iterable[str] = ("0x", "#"),
        acceptNoPrefix: bool = True,
        convertCase: Literal["lower", "upper"] | None = None,
    ) -> None:
        """
        Args:
            outputPrefix:
                Prefix prepended to the normalized output string.
            validPrefixes:
                Prefixes recognized as hex identifiers. The first matching prefix is stripped before
                validation and re-normalization.
            acceptNoPrefix:
                If `True`, inputs with no recognized prefix are accepted as bare hex strings.
            convertCase:
                If set, hex digits in the output are converted to the given case. `None` preserves
                the original case.
        """
        super().__init__(self._construct)
        self._outputPrefix = outputPrefix
        self._validPrefixes = tuple(validPrefixes)
        self._acceptNoPrefix = acceptNoPrefix
        self._convertCase = convertCase

    def _construct(self, value: str) -> str:
        """
        Normalizes a hex string to the output prefix and case.

        Raises:
            ValueError:
                `value` lacks a valid prefix while `acceptNoPrefix` is not set, or is not
                hexadecimal.
        """
        valuePrefix = None
        saneValue = value
        for prefix in self._validPrefixes:
            if value.startswith(prefix):
                valuePrefix = prefix
                saneValue = value[len(prefix) :]
                break
        if not self._acceptNoPrefix and valuePrefix is None:
            raise ValueError(
                f"Expected a hex with one of the prefixes {self._validPrefixes}; got `{value}`"
            )

        try:
            int(saneValue, 16)
        except Exception as e:
            raise ValueError(f"Expected a valid hexadecimal string; got `{value}`") from e

        if self._convertCase == "upper":
            saneValue = saneValue.upper()
        elif self._convertCase == "lower":
            saneValue = saneValue.lower()

        return f"{self._outputPrefix}{saneValue}"

    def __str__(self) -> str:
        return "hex"


class HexConstructor(CallableConstructor[[str], int]):
    """Converts hex strings into ints."""

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return False  # Ints are not necessarily hex

    def __init__(
        self, validPrefixes: Iterable[str] = ("0x", "#"), acceptNoPrefix: bool = True
    ) -> None:
        """
        Args:
            validPrefixes:
                Prefixes recognized as hex identifiers and stripped before parsing.
            acceptNoPrefix:
                If `True`, inputs with no recognized prefix are parsed as bare hex strings.
        """
        super().__init__(self._construct)
        self._validPrefixes = tuple(validPrefixes)
        self._acceptNoPrefix = acceptNoPrefix

    def _construct(self, value: str) -> int:
        """
        Converts a hex string into an int.

        Raises:
            ValueError:
                `value` lacks a valid prefix while `acceptNoPrefix` is not set, or is not
                hexadecimal.
        """
        for prefix in self._validPrefixes:
            if value.startswith(prefix):
                return int(value[len(prefix) :], 16)
        if self._acceptNoPrefix:
            return int(value, 16)
        raise ValueError(
            f"Expected a hex with one of the prefixes {self._validPrefixes}; got `{value}`"
        )

    def __str__(self) -> str:
        return "hex"


class IntOrHexConstructor(CallableConstructor[[str], int]):
    """
    Creates a constructor that converts clearly identified hex strings into int. Inputs that are not
    clearly identified as hex are treated as regular base10 ints.
    """

    @classmethod
    def can_handle(cls: type[Self], annotation: Any) -> bool:
        return False  # Plain `int` is not necessarily hex

    def __init__(self, validPrefixes: Iterable[str] = ("0x", "#")) -> None:
        """
        Args:
            validPrefixes:
                Prefixes that identify an input as hexadecimal. Inputs without a recognized prefix
                are parsed as base-10 integers.
        """
        super().__init__(self._construct)
        self._validPrefixes = tuple(validPrefixes)

    @property
    def _hex(self) -> HexConstructor:
        """The constructor for the inputs that carry a valid prefix."""
        return HexConstructor(self._validPrefixes, acceptNoPrefix=False)

    def _construct(self, value: str) -> int:
        """
        Converts a string into an int, as hex if it has a valid prefix and as base-10 otherwise.

        Raises:
            ValueError:
                `value` is neither a valid hex string nor a base-10 integer.
        """
        for prefix in self._validPrefixes:
            if value.startswith(prefix):
                return self._hex(value)
        return int(value)

    def __str__(self) -> str:
        return "int | hex"
