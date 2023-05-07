"""Requests related data models."""
from dataclasses import dataclass
from dataclasses import field
from enum import Enum

from bosch.control_panel.cc880p.utils import checksum
from bosch.control_panel.cc880p.utils import swap_nibbles


class RequestsProps(Enum):
    """Requests related properties."""

    StatusRequestCode = '01'
    StatusRequestSize = 11
    KeysRequestCode = '0C'
    KeysRequestSize = 11
    SetOutRequestCode = '0E'
    SetOutRequestSize = 11
    SetArmingRequestCode = '0E'
    SetArmingRequestSize = 11
    SetSirenRequestCode = '0E'
    SetSirenRequestSize = 11


@dataclass
class Request:
    """Base Request Class."""

    code: str
    size: int

    def encode(self, *args, **kwargs):
        """Encode the request. Should be overridden by child classes."""
        raise NotImplementedError('Implement the encode method')

    def _encode(self, data: bytes) -> bytes:
        """Encode bytes adding the request code and the checksum."""
        _data = bytes.fromhex(self.code) + data
        return _data + bytes([checksum(_data)])


@dataclass
class KeysRequest(Request):
    """Keys Request."""

    code: str = field(init=False, default=RequestsProps.KeysRequestCode.value)
    size: int = field(init=False, default=RequestsProps.KeysRequestSize.value)
    keys: bytes
    zone: int

    def encode(self):
        """Encode the Keys sending request."""
        # Remaining bytes after the keys should be 0
        empty = bytes([0x00] * (7 - len(self.keys)))
        zone = bytes([self.zone])
        n_keys = bytes([len(self.keys)])
        return self._encode(self.keys + empty + zone + n_keys)


@dataclass
class StatusRequest(Request):
    """Status Request."""

    code: str = field(
        init=False,
        default=RequestsProps.StatusRequestCode.value)
    size: int = field(
        init=False,
        default=RequestsProps.StatusRequestSize.value)
    installer_code: str

    def encode(self):
        """Encode the status request."""
        empty3 = bytes([0x00] * 3)
        empty2 = bytes([0x00] * 2)

        return self._encode(empty3 + self._encode_code() + empty2)

    def _encode_code(self):
        _code = self.installer_code + \
            ('f' * (7 - len(self.installer_code))) + '0'
        _code_bytes = bytes.fromhex(_code)
        return bytes(swap_nibbles(b) for b in _code_bytes)


@dataclass
class SetOutRequest(Request):
    """Set Output Request."""

    code: str = field(
        init=False,
        default=RequestsProps.SetOutRequestCode.value)
    size: int = field(
        init=False,
        default=RequestsProps.SetOutRequestSize.value)
    out_id: int
    on: bool

    def encode(self):
        """Encode the set output request."""
        empty7 = [0x00] * 7
        status = 0x03 if self.on else 0x04
        idx = self.out_id - 1
        return self._encode(bytes([status, idx, *empty7]))


@dataclass
class SetArmingRequest(Request):
    """Set Arming Request."""

    code: str = field(
        init=False,
        default=RequestsProps.SetArmingRequestCode.value)
    size: int = field(
        init=False,
        default=RequestsProps.SetArmingRequestSize.value)
    area_id: int
    arm: bool

    def encode(self):
        """Encode the set arming request."""
        empty7 = [0x00] * 7
        status = 0x01 if self.arm else 0x02
        idx = self.area_id - 1
        return self._encode(bytes([status, idx, *empty7]))


@dataclass
class SetSirenRequest(Request):
    """Set Siren Request."""

    code: str = field(
        init=False,
        default=RequestsProps.SetSirenRequestCode.value)
    size: int = field(
        init=False,
        default=RequestsProps.SetSirenRequestSize.value)
    on: bool

    def encode(self):
        """Encode the request to set the siren on/off."""
        empty8 = [0x00] * 8
        status = 0x05 if self.on else 0x06
        return self._encode(bytes([status, *empty8]))
