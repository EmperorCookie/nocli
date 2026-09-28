from collections.abc import Iterable
from typing import Any, Literal

from ._constructor import Constructor


class HexStringConstructor(Constructor):
    """Normalizes hex strings."""

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
        super().__init__(str)
        self._outputPrefix = outputPrefix
        self._validPrefixes = tuple(validPrefixes)
        self._acceptNoPrefix = acceptNoPrefix
        self._convertCase = convertCase

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (self._outputPrefix, self._validPrefixes, self._acceptNoPrefix, self._convertCase)

    def __call__(self, value: str) -> str:
        valuePrefix = None
        saneValue = value
        for prefix in self._validPrefixes:
            if value.startswith(prefix):
                valuePrefix = prefix
                saneValue = value[len(prefix) :]
                break
        if not self._acceptNoPrefix and valuePrefix is None:
            raise ValueError(
                f"Must provide a hex with one of the following prefixes: {self._validPrefixes}"
            )

        try:
            int(saneValue, 16)
        except Exception as e:
            raise ValueError("Must be a valid hexadecimal string.") from e

        if self._convertCase == "upper":
            saneValue = saneValue.upper()
        elif self._convertCase == "lower":
            saneValue = saneValue.lower()

        return super().__call__(f"{self._outputPrefix}{saneValue}")


class HexConstructor(Constructor):
    """Converts hex strings into ints."""

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
        super().__init__(int)
        self._validPrefixes = tuple(validPrefixes)
        self._acceptNoPrefix = acceptNoPrefix

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (self._validPrefixes, self._acceptNoPrefix)

    def __call__(self, value: str) -> int:
        for prefix in self._validPrefixes:
            if value.startswith(prefix):
                return super().__call__(value[len(prefix) :], 16)
        if self._acceptNoPrefix:
            return super().__call__(value, 16)
        raise ValueError(
            f"Must provide a hex with one of the following prefixes: {self._validPrefixes}"
        )


class IntOrHexConstructor(Constructor):
    """
    Creates a constructor that converts clearly identified hex strings into int. Inputs that are not
    clearly identified as hex are treated as regular base10 ints.
    """

    def __init__(self, validPrefixes: Iterable[str] = ("0x", "#")) -> None:
        """
        Args:
            validPrefixes:
                Prefixes that identify an input as hexadecimal. Inputs without a recognized prefix
                are parsed as base-10 integers.
        """
        super().__init__(int)
        self._validPrefixes = tuple(validPrefixes)

    @property
    def _eqFields(self) -> tuple[Any, ...]:
        return (self._validPrefixes,)

    def __call__(self, value: str) -> int:
        for prefix in self._validPrefixes:
            if value.startswith(prefix):
                return super().__call__(value[len(prefix) :], 16)
        return super().__call__(value)
