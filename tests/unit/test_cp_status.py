import pytest
from bosch.control_panel.cc880p.cp import CP


def test_is_status_msg(
    control_panel: CP
):
    # When is a status message
    assert control_panel._is_status_msg(bytes([0x04] + [0] * 12)) is True

    # When is not a status messate
    assert control_panel._is_status_msg(bytes([0x03] + [0] * 10)) is False

    # When is a status message but wrong size
    with pytest.raises(ValueError):
        assert control_panel._is_status_msg(bytes([0x04])) is True
