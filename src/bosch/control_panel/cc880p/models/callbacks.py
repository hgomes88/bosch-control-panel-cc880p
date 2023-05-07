"""Callbacks."""
from typing import Callable

from bosch.control_panel.cc880p.models.constants import Id
from bosch.control_panel.cc880p.models.cp import ControlPanelEntity


"""Control Panel Listener."""
ControlPanelListener = Callable[[Id, ControlPanelEntity], bool]
"""Data Listener."""
DataListener = Callable[[bytes], bool]
