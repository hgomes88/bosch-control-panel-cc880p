from typing import Union


def to_hex(_bytes: Union[bytes, int]) -> str:
    """ Converts a single byte or a list of bytes into hex format

    Args:
        _bytes (bytes|int): Single byte or a list of bytes

    Returns:
        str: String representation of the byte(s) in hexadecimal format
    """

    _byte_str = ""
    if isinstance(_bytes, int):
        _bytes = bytes([_bytes])

    for _byte in _bytes:
        _byte_str += f"{int(_byte):02x}"
        _byte_str += " "
    return _byte_str


def to_bin(_bytes: Union[bytes, int]):
    """ Converts a single byte or a list of bytes into binary format

    Args:
        _bytes (bytes|int): Single byte or a list of bytes

    Returns:
        str: String representation of the byte(s) in binary format
    """
    _byte_str = ""
    if isinstance(_bytes, int):
        _bytes = bytes([_bytes])

    for _byte in _bytes:
        _byte_str += f"{int(_byte):08b}"
        _byte_str += " "
    return _byte_str