from bosch.control_panel.cc880p.cp import CP
from bosch.control_panel.cc880p.models.cp import ArmingMode


def test_init_control_panel(
    control_panel: CP
):
    cp = control_panel.control_panel

    assert cp.siren.on is False

    for i in range(1, len(cp.areas)):
        area = cp.areas[i]
        assert area.mode == ArmingMode.DISARMED

    for i in range(1, len(cp.zones)):
        zone = cp.zones[i]
        assert zone.triggered is False
        assert zone.enabled is False

    for i in range(1, len(cp.outputs)):
        output = cp.outputs[i]
        assert output.on is False


def test_call_str_returns_repr(
    control_panel: CP
):
    assert str(control_panel) is not None


def test_call_dict_returns_dict(
    control_panel: CP
):
    cp_dict = control_panel.__dict__
    cp = control_panel.control_panel

    assert cp_dict['siren']['on'] is cp.siren.on

    for i in range(1, len(cp.areas) + 1):
        area = cp_dict['areas'][i]
        assert area['mode'] == cp.areas[i].mode.name

    for i in range(1, len(cp.zones) + 1):
        zone = cp_dict['zones'][i]
        assert zone['triggered'] is cp.zones[i].triggered
        assert zone['enabled'] is cp.zones[i].enabled

    for i in range(1, len(cp.outputs) + 1):
        output = cp_dict['outputs'][i]
        assert output['on'] is cp.outputs[i].on
