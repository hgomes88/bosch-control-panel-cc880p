import pytest
from bosch.control_panel.cc880p.cp import CP
from bosch.control_panel.cc880p.models import ArmingMode

from tests.utils import get_check_bits


def _zone_triggered_update_data():
    # Maximum 16 zones
    for i in range(16):
        # Two bytes used for the zones
        bytes = [0x00, 0x00]
        # Bits from 0-7
        bit = i % 8
        # Bytes:
        # 1st byte - zones 1-8
        # 2nd byte - zones 9-16
        byte = int(i / 8)

        # Set the bit of the output to enable it
        bytes[byte] = 1 << bit
        # Retreive the tuples with the data to test, and the expected status
        for data in get_check_bits(*bytes):
            yield (i + 1, ) + data


@pytest.mark.parametrize(
    'zone_number, data, zone_status',
    _zone_triggered_update_data()
)
def test_zone_triggered_update(
    data: bytes,
    zone_number: int,
    zone_status: bool,
    control_panel: CP
):
    control_panel._update_zone_status(data)
    assert control_panel.control_panel.zones[
        zone_number
    ].triggered is zone_status


def _zone_enabled_update_data():

    for area_mode in [e for e in ArmingMode]:
        # Maximum 16 zones
        for i in range(1):
            # Two bytes used for the zones
            bytes = [0x00, 0x00]
            # Bits from 0-7
            bit = i % 8
            # Bytes:
            # 1st byte - zones 1-8
            # 2nd byte - zones 9-16
            byte = int(i / 8)

            # Retreive the tuples with the data to test, and the expected
            # status
            bytes[byte] = 1 << bit

            for data in get_check_bits(*bytes):
                if area_mode == ArmingMode.ARMED_AWAY:
                    data = (data[0], True)
                if area_mode == ArmingMode.DISARMED:
                    data = (data[0], False)

                yield (i + 1, ) + data + (area_mode,)


@pytest.mark.parametrize(
    'zone_number, data, zone_status, area_mode',
    _zone_enabled_update_data()
)
def test_zone_enabled_update(
    data: bytes,
    zone_number: int,
    zone_status: bool,
    area_mode: ArmingMode,
    control_panel: CP
):
    # Set the proper area mode
    control_panel.control_panel.areas[1].mode = area_mode
    control_panel.update_zone_enabled(data)

    assert control_panel.control_panel.zones[
        zone_number
    ].enabled is zone_status
