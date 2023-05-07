"""Utilities."""
from typing import Tuple
from typing import Union


def odd_parity(n: int) -> bool:
    """Calculate the odd parity of a certain byte."""
    y = n ^ (n >> 1)
    y = y ^ (y >> 2)
    y = y ^ (y >> 4)
    y = y ^ (y >> 8)
    y = y ^ (y >> 16)

    if (y & 1):
        return True
    return False


def parities(data: bytes) -> Tuple[int, int]:
    """Calculate the number of odd and even parities."""
    odds = 0
    evens = 0
    for d in data:
        if odd_parity(d):
            odds += 1
        else:
            evens += 1

    return odds, evens


def evens(data: bytes) -> int:
    """Return the number of even parities."""
    _, evens = parities(data)
    return evens


def odds(data: bytes) -> int:
    """Return the number of odd parities."""
    odds, _ = parities(data)
    return odds


def checksum(data: bytes) -> int:
    """Calculate the checksum of a set of bytes."""
    return (sum(data) + evens(data)) & 0xFF


def swap_nibbles(x):
    """Swap byte nibbles."""
    return ((x & 0x0F) << 4 | (x & 0xF0) >> 4)


def to_hex(_bytes: Union[bytes, int]) -> str:
    """Convert a single byte or a list of bytes into hex format.

    Args:
        _bytes (bytes|int): Single byte or a list of bytes

    Returns:
        str: String representation of the byte(s) in hexadecimal format
    """
    _byte_str = ''
    if isinstance(_bytes, int):
        _bytes = bytes([_bytes])

    for _byte in _bytes:
        _byte_str += f'{int(_byte):02x}'
        _byte_str += ' '
    return _byte_str


def to_bin(_bytes: Union[bytes, int]):
    """Convert a single byte or a list of bytes into binary format.

    Args:
        _bytes (bytes|int): Single byte or a list of bytes

    Returns:
        str: String representation of the byte(s) in binary format
    """
    _byte_str = ''
    if isinstance(_bytes, int):
        _bytes = bytes([_bytes])

    for _byte in _bytes:
        _byte_str += f'{int(_byte):08b}'
        _byte_str += ' '
    return _byte_str
