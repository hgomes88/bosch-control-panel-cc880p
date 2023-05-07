"""Responses data models."""
import datetime
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import List

from bosch.control_panel.cc880p.models.cp import ArmingMode
from bosch.control_panel.cc880p.models.cp import CpModel


class ResponsesProps(Enum):
    """Responses properties."""

    StatusCode = '04'
    StatusSize = 13


@dataclass
class Response:
    """Response base object."""

    code: str
    size: int


@dataclass
class StatusResponse:
    """Status response object."""

    code: str = field(init=False, default=ResponsesProps.StatusCode.value)
    size: int = field(init=False, default=ResponsesProps.StatusSize.value)
    time: datetime.time
    siren: bool
    outs: List[bool]
    areas: List[ArmingMode]
    zones: List[bool]
    zones_en: List[bool]

    @classmethod
    def decode(cls, data: bytes, cp: CpModel):
        """Decode a status response."""
        time = cls._decode_time(data)
        siren = cls._decode_siren_status(data)
        outs = cls._decode_outputs(data, cp.n_outputs)
        areas = cls._decode_areas(data, cp.n_areas)
        zones = cls._decode_zones(data, cp.n_zones)
        zones_en = cls._decode_zones_en(data, cp.n_zones, areas[0])

        return StatusResponse(
            time=time,
            siren=siren,
            outs=outs,
            areas=areas,
            zones=zones,
            zones_en=zones_en
        )

    @classmethod
    def _decode_time(cls, data: bytes) -> datetime.time:
        bytes = data[10:12]
        # Hours
        hours = bytes[0] & 0x1F  # Only the first 5 bits matters (0h-23h)
        # Minutes
        minutes = bytes[1] & 0x3F  # Only the first 6 bits matters (0m-59m)
        # Time
        return datetime.time(hour=hours, minute=minutes)

    @classmethod
    def _decode_siren_status(cls, data: bytes) -> bool:
        _byte = data[10]
        bit = 6

        return bool(_byte & (1 << bit))

    @classmethod
    def _decode_outputs(cls, data: bytes, n_outputs: int):
        outs: List[bool] = []
        bytes = data[1:3]

        for i in range(n_outputs):
            bit = i % 8
            byte = len(bytes) - int(i / 8) - 1

            outs.append(bool(bytes[byte] & (1 << bit)))

        return outs

    @classmethod
    def _decode_areas(cls, data: bytes, n_areas: int):
        areas: List[ArmingMode] = []
        _byte = data[9]

        for i in range(n_areas):
            away_bit = i % 4
            stay_bit = away_bit + 4
            away_status = bool(_byte & (1 << away_bit))
            stay_status = bool(_byte & (1 << stay_bit))

            if away_status:
                area = ArmingMode.ARMED_AWAY
            elif stay_status:
                area = ArmingMode.ARMED_STAY
            else:
                area = ArmingMode.DISARMED

            areas.append(area)

        return areas

    @classmethod
    def _decode_zones(cls, data: bytes, n_zones: int):
        bytes = data[3:5]
        zones: List[bool] = []

        for i in range(n_zones):
            bit = i % 8
            byte = int(i / 8)

            zones.append(bool(bytes[byte] & (1 << bit)))

        return zones

    @classmethod
    def _decode_zones_en(cls, data: bytes, n_zones: int, area: ArmingMode):
        bytes = data[5:7]
        zones_en: List[bool] = []
        status = False

        if area == ArmingMode.ARMED_AWAY:
            status = True
        elif area == ArmingMode.DISARMED:
            status = False

        for i in range(n_zones):
            bit = i % 8
            byte = int(i / 8)

            if area == ArmingMode.ARMED_STAY:
                status = bool(bytes[byte] & (1 << bit))

            zones_en.append(status)

        return zones_en
