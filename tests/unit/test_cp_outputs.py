import pytest
from bosch.control_panel.cc880p.cp import CP


def _output_status_update_data():
    return [
        (
            '043460000000000000001001b1',
            [False, False, False, False, False]
        ),
        (
            '043461000000000000001001b1',
            [True, False, False, False, False]
        ),
        (
            '04346200000000000000100fc1',
            [False, True, False, False, False]
        ),
        (
            '043464000000000000001012c6',
            [False, False, True, False, False]
        ),
        (
            '043468000000000000001016cd',
            [False, False, False, True, False]
        ),
        (
            '043470000000000000001018d8',
            [False, False, False, False, True]
        ),
        (
            '04347f000000000000001018e7',
            [True, True, True, True, True]
        ),
        (
            '043472000000000000001018db',
            [False, True, False, False, True]
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'data, outs_status',
    _output_status_update_data()
)
async def test_output_status_update(
    data: str,
    outs_status: bool,
    control_panel: CP,
    reader
):
    reader.return_value.readexactly.return_value = bytes.fromhex(data)
    await control_panel.get_status()

    cp_outs = control_panel.control_panel.outputs.values()

    assert [out_status.on for out_status in cp_outs] == outs_status
