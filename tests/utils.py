def get_check_bits(*bytes_mask: int):
    """Gets test data returning true if the mask matches
    """

    n_bytes = len(bytes_mask)
    for byte in range(n_bytes):
        for bit in range(8):
            ba = bytearray(n_bytes)
            ba[byte] = 1 << bit
            b = bytes(ba)
            yield (b, bool(b == bytes(bytes_mask)))
