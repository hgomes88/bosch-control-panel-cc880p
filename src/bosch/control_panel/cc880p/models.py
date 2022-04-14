import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from typing import Dict

Id = int


@dataclass
class ControlPanelModel:
    pass


@dataclass
class Siren(ControlPanelModel):
    """ Dataclass to store the Siren of the alarm
    """

    on: bool = False


@dataclass
class Zone(ControlPanelModel):
    """ Dataclass to store the zones of the alarm
    """

    triggered: bool = False
    enabled: bool = False


@dataclass
class Output(ControlPanelModel):
    """Dataclass to store the varios alarm output states
    """

    on: bool = False


class ArmingMode(Enum):
    """Enumerator with all the alarm states
    """

    DISARMED = 0
    ARMED_AWAY = 1
    ARMED_STAY = 2


@dataclass
class Area(ControlPanelModel):
    """Dataclass representing the alarm area
    """

    mode: ArmingMode = ArmingMode.DISARMED


class Time(datetime.time):
    pass


@dataclass
class ControlPanel(ControlPanelModel):
    """Dataclass representing the control panel object
    """
    siren: Siren
    areas: Dict[Id, Area]
    zones: Dict[Id, Zone]
    outputs: Dict[Id, Output]
    time_utc: Time


ControlPanelListener = Callable[[Id, ControlPanelModel], bool]
DataListener = Callable[[bytes], bool]
