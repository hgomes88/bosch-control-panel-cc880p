from dataclasses import dataclass
from enum import Enum
from typing import Callable

Id = int

@dataclass
class Zone:
    """ Dataclass to store the zones of the alarm
    """

    number: Id
    name: str = ""
    triggered = False


@dataclass
class Output:
    """Dataclass to store the varios alarm output states
    """

    number: Id
    name: str = ""
    on = False


class ArmingMode(Enum):
    """Enumarator with all the alarm states
    """

    DISARMED = 0
    ARMED_AWAY = 1
    ARMED_STAY = 2


@dataclass
class Area:
    """Dataclass representig the alarm area
    """

    number: Id
    name: str = ""
    mode: ArmingMode = ArmingMode.DISARMED


ZoneListener = Callable[[Zone], bool]
AreaListener = Callable[[Area], bool]
SirenListener = Callable[[bool], bool]