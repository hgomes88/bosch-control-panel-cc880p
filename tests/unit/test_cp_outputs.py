import pytest
from bosch.control_panel.cc880p.cp import CP

from tests.utils import get_check_bits


def _output_status_update_data():
    # Maximum 14 outputs
    for i in range(14):
        # Two bytes used for the outputs
        bytes = [0x00, 0x00]
        # Bits from 0-7
        bit = i % 8
        # Bytes:
        # 1st byte - outputs 9-14
        # 2nd byte - outputs 1-8
        byte = len(bytes) - int(i / 8) - 1

        # Set the bit of the output to enable it
        bytes[byte] = 1 << bit
        # Retreive the tuples with the data to test, and the expected status
        for data in get_check_bits(*bytes):
            yield (i + 1, ) + data


@pytest.mark.parametrize(
    'output_number, data, out_status',
    _output_status_update_data()
)
def test_output_status_update(
    data: bytes,
    output_number: int,
    out_status: bool,
    control_panel: CP
):
    control_panel._update_output_status(data)
    assert control_panel.control_panel.outputs[output_number].on is out_status
