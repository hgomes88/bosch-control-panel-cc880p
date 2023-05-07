import pytest
from bosch.control_panel.cc880p.cp import CP


def _zone_triggered_update_data():
    return [
        (
            '043460000000000000000e2cda',
            [
                False, False, False, False, False, False, False, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (

            '043460010000000000000e36e5',
            [
                True, False, False, False, False, False, False, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460020000000000000e36e6',
            [
                False, True, False, False, False, False, False, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460040000000000000e36e8',
            [
                False, False, True, False, False, False, False, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460080000000000000e36ec',
            [
                False, False, False, True, False, False, False, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460100000000000000e36f4',
            [
                False, False, False, False, True, False, False, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460200000000000000e3604',
            [
                False, False, False, False, False, True, False, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460400000000000000e3624',
            [
                False, False, False, False, False, False, True, False,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460800000000000000e3664',
            [
                False, False, False, False, False, False, False, True,
                False, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460000100000000000e2cda',
            [
                False, False, False, False, False, False, False, False,
                True, False, False, False, False, False, False, False
            ]
        ),
        (
            '043460000200000000000e2cdb',
            [
                False, False, False, False, False, False, False, False,
                False, True, False, False, False, False, False, False
            ]
        ),
        (
            '043460000400000000000e2cdd',
            [
                False, False, False, False, False, False, False, False,
                False, False, True, False, False, False, False, False
            ]
        ),
        (
            '043460000800000000000e2ce1',
            [
                False, False, False, False, False, False, False, False,
                False, False, False, True, False, False, False, False
            ]
        ),
        (
            '043460001000000000000e2ce9',
            [
                False, False, False, False, False, False, False, False,
                False, False, False, False, True, False, False, False
            ]
        ),
        (
            '043460002000000000000e2cf9',
            [
                False, False, False, False, False, False, False, False,
                False, False, False, False, False, True, False, False
            ]
        ),
        (
            '043460004000000000000e2c19',
            [
                False, False, False, False, False, False, False, False,
                False, False, False, False, False, False, True, False
            ]
        ),
        (
            '043460008000000000000e2c59',
            [
                False, False, False, False, False, False, False, False,
                False, False, False, False, False, False, False, True
            ]
        ),
        (
            '043460a55a00000000000e2cd9',
            [
                True, False, True, False, False, True, False, True,
                False, True, False, True, True, False, True, False
            ]
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'data, zones_status',
    _zone_triggered_update_data()
)
async def test_zone_triggered_update(
    data: str,
    zones_status: bool,
    control_panel: CP,
    reader
):

    reader.return_value.readexactly.return_value = bytes.fromhex(data)
    await control_panel.get_status()

    cp_zones = control_panel.control_panel.zones.values()

    assert [zone_status.triggered for zone_status in cp_zones] == zones_status
