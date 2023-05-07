import pytest
from bosch.control_panel.cc880p.cp import CP


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'data, siren_status',
    [
        ('043460000000000000004d2110', True),
        ('043460000000000000000d27d5', False),
    ]
)
async def test_siren_status_update(
    data: str,
    siren_status: bool,
    control_panel: CP,
    reader
):
    reader.return_value.readexactly.return_value = bytes.fromhex(data)
    await control_panel.get_status()
    assert control_panel.control_panel.siren.on is siren_status
