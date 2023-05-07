"""Control panel models."""
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict

from bosch.control_panel.cc880p.models.constants import Id


@dataclass
class CpModel:
    """Control Panel model properties."""

    n_zones: int
    n_areas: int
    n_outputs: int


class CpVersion(Enum):
    """Control Panel Version to be used.

    Returns a Control Panel model object with the properties referred to
    the selected version
    """

    S16_V14 = CpModel(
        n_zones=16,
        n_areas=1,
        n_outputs=5
    )

    def model(self) -> CpModel:
        """Return the CpModel object."""
        return self.value


@dataclass
class ControlPanelEntity:
    """Model representing a Control Panel entity."""


@dataclass
class Siren(ControlPanelEntity):
    """Dataclass to store the Siren of the alarm."""

    on: bool = False


@dataclass
class Zone(ControlPanelEntity):
    """Dataclass to store the zones of the alarm."""

    triggered: bool = False
    enabled: bool = False


@dataclass
class Output(ControlPanelEntity):
    """Dataclass to store the various alarm output states."""

    on: bool = False


@dataclass
class Availability(ControlPanelEntity):
    """Dataclass to store the various alarm output states."""

    available: bool = False


class ArmingMode(Enum):
    """Enumerator with all the alarm states."""

    DISARMED = 0
    ARMED_AWAY = 1
    ARMED_STAY = 2


@dataclass
class Area(ControlPanelEntity):
    """Dataclass representing the alarm area."""

    mode: ArmingMode = ArmingMode.DISARMED


class Time(datetime.time):
    """Datetime."""


@dataclass
class ControlPanel(ControlPanelEntity):
    """Dataclass representing the control panel object."""

    siren: Siren
    areas: Dict[Id, Area]
    zones: Dict[Id, Zone]
    outputs: Dict[Id, Output]
    time_utc: Time
    availability: Availability

    @staticmethod
    def build(model: CpModel) -> 'ControlPanel':
        """Build a control panel object."""
        return ControlPanel(
            siren=Siren(),
            outputs={i + 1: Output() for i in range(model.n_outputs)},
            areas={i + 1: Area() for i in range(model.n_areas)},
            zones={i + 1: Zone() for i in range(model.n_zones)},
            time_utc=Time(),
            availability=Availability()
        )
