import pytest

import nocli


class TestHexString:
    def test_0x(self):
        assert nocli.constructors.HexStringConstructor()("0xff") == "0xff"

    def test_hash(self):
        assert nocli.constructors.HexStringConstructor()("#ff") == "0xff"

    def test_bare(self):
        assert nocli.constructors.HexStringConstructor()("ff") == "0xff"

    def test_bare_rejected(self):
        with pytest.raises(ValueError):
            nocli.constructors.HexStringConstructor(acceptNoPrefix=False)("ff")

    def test_upper(self):
        assert nocli.constructors.HexStringConstructor(convertCase="upper")("0xab") == "0xAB"

    def test_lower(self):
        assert nocli.constructors.HexStringConstructor(convertCase="lower")("0xAB") == "0xab"

    def test_invalid(self):
        with pytest.raises(ValueError):
            nocli.constructors.HexStringConstructor()("0xzz")

    def test_output_prefix(self):
        assert nocli.constructors.HexStringConstructor(outputPrefix="#")("0xff") == "#ff"

    def test_declines(self):
        assert not nocli.constructors.HexStringConstructor.can_handle(str)

    def test_str(self):
        assert str(nocli.constructors.HexStringConstructor()) == "hex"


class TestHex:
    def test_0x(self):
        assert nocli.constructors.HexConstructor()("0xff") == 255

    def test_hash(self):
        assert nocli.constructors.HexConstructor()("#ff") == 255

    def test_bare(self):
        assert nocli.constructors.HexConstructor()("ff") == 255

    def test_bare_rejected(self):
        with pytest.raises(ValueError):
            nocli.constructors.HexConstructor(acceptNoPrefix=False)("ff")

    def test_declines(self):
        assert not nocli.constructors.HexConstructor.can_handle(int)

    def test_str(self):
        assert str(nocli.constructors.HexConstructor()) == "hex"


class TestIntOrHex:
    def test_decimal(self):
        assert nocli.constructors.IntOrHexConstructor()("255") == 255

    def test_0x(self):
        assert nocli.constructors.IntOrHexConstructor()("0xff") == 255

    def test_hash(self):
        assert nocli.constructors.IntOrHexConstructor()("#ff") == 255

    def test_invalid(self):
        with pytest.raises(ValueError):
            nocli.constructors.IntOrHexConstructor()("abc")

    def test_declines(self):
        assert not nocli.constructors.IntOrHexConstructor.can_handle(int)

    def test_str(self):
        assert str(nocli.constructors.IntOrHexConstructor()) == "int | hex"
