import pytest
from bosch.control_panel.cc880p.cp import CP

from tests.utils import get_check_bits


def _siren_status_update_data():
    yield from get_check_bits(0x40)


@pytest.mark.parametrize('data, siren_status', _siren_status_update_data())
def test_siren_status_update(
    data: bytes,
    siren_status: bool,
    control_panel: CP
):
    control_panel._update_siren_status(data[0])
    assert control_panel.control_panel.siren.on is siren_status
