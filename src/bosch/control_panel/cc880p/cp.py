"""Control Panel."""
import asyncio
import dataclasses
import logging
from asyncio import AbstractEventLoop
from enum import Enum
from typing import List
from typing import Optional
from typing import Type
from typing import Union

from bosch.control_panel.cc880p.models.callbacks import ControlPanelListener
from bosch.control_panel.cc880p.models.callbacks import DataListener
from bosch.control_panel.cc880p.models.constants import Id
from bosch.control_panel.cc880p.models.constants import MAX_KEYS
from bosch.control_panel.cc880p.models.cp import ArmingMode
from bosch.control_panel.cc880p.models.cp import ControlPanel
from bosch.control_panel.cc880p.models.cp import CpModel
from bosch.control_panel.cc880p.models.cp import Time
from bosch.control_panel.cc880p.models.requests import KeysRequest
from bosch.control_panel.cc880p.models.requests import Request
from bosch.control_panel.cc880p.models.requests import SetArmingRequest
from bosch.control_panel.cc880p.models.requests import SetOutRequest
from bosch.control_panel.cc880p.models.requests import SetSirenRequest
from bosch.control_panel.cc880p.models.requests import StatusRequest
from bosch.control_panel.cc880p.models.responses import Response
from bosch.control_panel.cc880p.models.responses import StatusResponse
from bosch.control_panel.cc880p.utils import checksum
from bosch.control_panel.cc880p.utils import to_hex

_LOGGER = logging.getLogger(__name__)


class CP:
    """Alarm control panel object representation."""

    def __init__(
        self,
        ip: str,
        port: int,
        model: CpModel,
        installer_code: str = None,
        loop: Optional[AbstractEventLoop] = None,
    ):
        """Initialize the Control Panel object to interface through TCP.

        Args:
            ip (str):
                IP of the control panel
            port (int):
                Port of the control panel
            mode (CpModel):
                Control Panel Model.
            loop (AbstractEventLoop, optional):
                Event Loop. Defaults None.
        """
        # Main event loop
        self._loop = loop or asyncio.get_event_loop()

        # Control Panel model
        self._model = model

        # Installer code needed to fetch control panel statuses
        self._installer_code = installer_code

        # IP of the control panel
        self._ip = ip
        # Port of the control panel
        self._port = port

        # Streamreader
        self._reader: Optional[asyncio.StreamReader] = None
        # Streamwriter
        self._writer: Optional[asyncio.StreamWriter] = None

        # Lock
        self._lock = asyncio.Lock()

        # Listeners to be called whenever the control panel state is changed
        self._control_panel_listeners: List[ControlPanelListener] = []
        # Listeners to be called whenever the there's new data
        self._data_listeners: List[DataListener] = []

        self._control_panel = ControlPanel.build(self._model)

    def __repr__(self):
        """Representation of control panel."""
        return str(self._control_panel)

    @property
    def __dict__(self):
        """Return a dict representation of control panel."""
        def _custom_asdict_factory(data):
            def convert_value(obj):
                if isinstance(obj, Enum):
                    return obj.name
                return obj

            return {k: convert_value(v) for k, v in data}

        return dataclasses.asdict(
            self._control_panel,
            dict_factory=_custom_asdict_factory
        )

    @property
    def control_panel(self) -> ControlPanel:
        """Property that returns the control panel object."""
        return self._control_panel

    async def start(self) -> 'CP':
        """Establish the connection to the control panel."""
        # Open the connection to the control panel
        await self._open_connection()
        return self

    async def stop(self) -> 'CP':
        """Stop the connection to the control panel."""
        return self

    def add_control_panel_listener(self, listener: ControlPanelListener):
        """Add a listener function to listen for any change in the alarm."""
        self._control_panel_listeners.append(listener)

    def add_data_listener(self, listener: DataListener):
        """Add a listener function to listen for any incoming data."""
        self._data_listeners.append(listener)

    async def send_keys(
        self,
        keys: Union[str, List[str]],
    ):
        """Simulate a keypad, allowing sending multiple keys."""
        encoded_keys = self._encode_keys(keys)

        for i in range(0, len(encoded_keys), MAX_KEYS):
            # Get the next keys subset
            keys_subset = encoded_keys[i: i + MAX_KEYS]
            # Build the request
            request = KeysRequest(keys=keys_subset, zone=0)
            # Send the request
            await self.send_request(request, StatusResponse)

    async def set_output(self, id: Id, on: bool):
        """Set output."""
        try:
            if id not in self.control_panel.outputs:
                raise ValueError(f"The output with {id} doesn't exist")

            if self._control_panel.outputs[id].on != on:
                request = SetOutRequest(id, on)
                await self.send_request(request, StatusResponse)
        except Exception as ex:
            _LOGGER.error(f'Error setting the output: {ex}')
            raise

    async def set_arming(
        self,
        id: Id = 1,
        arm: bool = False
    ):
        """Set arming."""
        if arm and self._control_panel.areas[id].mode == ArmingMode.DISARMED:
            request = SetArmingRequest(id, arm)
            await self.send_request(request, StatusResponse)

        elif not arm and \
                self._control_panel.areas[id].mode != ArmingMode.DISARMED:
            request = SetArmingRequest(id, arm)
            await self.send_request(request, StatusResponse)

    async def set_siren(self, on: bool = False):
        """Set siren on or off.."""
        if on and self._control_panel.siren.on != on:
            # Switch on the siren
            await self.send_request(SetSirenRequest(on), StatusResponse)
        elif not on and self._control_panel.siren.on != on:
            # Switch of the siren
            await self.send_request(SetSirenRequest(on), StatusResponse)

    async def get_status(self):
        """Command to request the status of the alarm."""
        request = StatusRequest(installer_code=self._installer_code)
        await self.send_request(request, StatusResponse)

    async def send_request(
            self,
            request: Request,
            resp_type: Optional[Type[Response]] = None
    ):
        """Send a new request."""
        n_resp_bytes = resp_type.size if resp_type else 1
        resp = await self.send_command(
            message=request.encode(),
            n_resp_bytes=n_resp_bytes,
            timeout=3
        )
        if resp:
            if resp_type:
                if len(resp) != resp_type.size:
                    raise ValueError(
                        f'The size of the frame should be {resp_type.size}'
                        f' but is {len(resp)}'
                    )
            self._handle_data(resp)

    async def send_command(
        self,
        message: bytes,
        n_resp_bytes=0,
        timeout=3
    ) -> Optional[bytes]:
        """Send a command to the alarm and returns its response.

        Args:
            message (bytes):
                Message to send to the control panel

        Returns:
            bytes:
                Response of the message sent to the control panel or None
                otherwise
        """
        resp = None
        available = False

        async with self._lock:
            try:
                resp = await self._send(message, n_resp_bytes, timeout)
            except asyncio.exceptions.TimeoutError:
                _LOGGER.warning('Message not received on time')
                raise
            except asyncio.IncompleteReadError:
                _LOGGER.warning('Message not received.')
                raise
            except ConnectionResetError:
                _LOGGER.warning('Connection reset by peer')
                raise
            except EOFError:
                _LOGGER.warning('Connection EOF')
                raise
            except BaseException as ex:
                _LOGGER.warning('Unexpected Error: %s', ex)
                raise
            else:
                available = True
                return resp
            finally:
                if self.control_panel.availability.available != available:
                    self.control_panel.availability.available = available
                    for listener in self._control_panel_listeners:
                        asyncio.create_task(
                            listener(0, self.control_panel.availability)
                        )

    async def _open_connection(self):
        """Open the stream connection to the alarm."""
        _LOGGER.info('Connecting to control panel...')
        try:
            if self._reader:
                if not self._reader.at_eof():
                    self._reader.feed_eof()

            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()

            self._reader, self._writer = await asyncio.open_connection(
                self._ip,
                self._port
            )
        except ConnectionRefusedError:
            _LOGGER.error('Connection to control panel failed')
            raise
        except asyncio.TimeoutError:
            _LOGGER.error('Connection to control panel timed out')
            raise
        except BaseException:
            _LOGGER.error(
                'Connection to control panel failed with unknown error')
            raise

    async def _send(
        self,
        message: bytes,
        n_resp_bytes: int = 0,
        timeout=3
    ) -> bytes:
        """Send a binary stream to the control panel and waits for its response.

        Args:
            message (bytes): Message to send to the control panel

        Returns:
            bytes: Response of the message sent to the control panel
        """
        if self._reader and self._writer:
            # Ensure a clean buffer
            self._reader._buffer.clear()  # type: ignore

            # Send the command
            self._writer.write(message)
            await self._writer.drain()

            # Wait for a response
            if not self._reader.at_eof():
                # data = await asyncio.wait_for(self._reader.read(32),
                # timeout=2)
                if n_resp_bytes:
                    data = await asyncio.wait_for(
                        self._reader.readexactly(n_resp_bytes),
                        timeout=timeout
                    )
                else:
                    data = await asyncio.wait_for(
                        self._reader.read(32), timeout=timeout
                    )
                if not data:
                    raise asyncio.IncompleteReadError(data, 32)
                return data
            else:
                raise EOFError()
        else:
            raise RuntimeError('Stream not initialized')

    def _encode_key(self, key: str) -> int:
        # Is a number between 0 and 9
        if key.isdigit() and int(key) in range(0, 10):
            return int(key)
        elif key == '*':
            return 0x1B
        elif key == '#':
            return 0x1A
        else:
            _LOGGER.error('Unrecognized key %s', key)
            raise ValueError('Unrecognized key %s', key)

    def _encode_keys(self, keys: Union[str, List[str]]) -> bytes:
        return bytes(self._encode_key(key) for key in list(keys))

    def _validate_data(self, data: Optional[bytes]):
        if data:
            cs = checksum(data[0:-1])
            if cs != data[-1]:
                raise ValueError(
                    f'Data with invalid checksum. Received: {hex(data[-1])}, '
                    f'Calculated: {hex(cs)} ({data.hex()})'
                )
        else:
            raise RuntimeError('Checksum cannot be calculated without data')

    def _handle_data(self, data: Optional[bytes]):
        if data:

            self._validate_data(data)

            _LOGGER.debug('New Data: %s', to_hex(data))

            if self._is_status_msg(data):
                self._handle_status_msg(data)

            for listener in self._data_listeners:
                asyncio.create_task(listener(data))
        else:
            _LOGGER.warn('No Data Received!!!')

    @classmethod
    def _is_status_msg(cls, data: bytes):

        if bytes([data[0]]) != bytes.fromhex(StatusResponse.code):
            return False

        if len(data) != StatusResponse.size:
            raise ValueError(
                f'The size of the frame should be {StatusResponse.size}'
                f' but is {len(data)}'
            )

        return True

    def _handle_status_msg(self, data: bytes):
        resp = StatusResponse.decode(data, self._model)

        self._update_siren_status(resp.siren)
        self._update_output_status(resp.outs)
        self._update_area_status(resp.areas)
        self._update_zone_status(resp.zones)
        self.update_zone_enabled(resp.zones_en)
        self._update_time(resp.time)

    def _update_zone_status(self, zones: List[bool]):
        for i in range(self._model.n_zones):
            zone_number: Id = i + 1
            zone = self._control_panel.zones[zone_number]

            if zone.triggered != zones[i]:
                zone.triggered = zones[i]

                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(zone_number, zone))

                _LOGGER.info(
                    'Status of Zone %d changed to %d',
                    zone_number,
                    zone.triggered
                )

    def update_zone_enabled(self, zones_en: List[bool]):
        """Update zone enabled."""
        for i in range(self._model.n_zones):
            zone_number = i + 1
            zone = self._control_panel.zones[zone_number]

            if zone.enabled != zones_en[i]:
                zone.enabled = zones_en[i]

                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(zone_number, zone))

                _LOGGER.info(
                    'Zone enabling of Zone %d changed to %d',
                    zone_number,
                    zone.enabled
                )

    def _update_siren_status(self, status: bool):
        if self._control_panel.siren.on != status:
            self._control_panel.siren.on = status

            for listener in self._control_panel_listeners:
                asyncio.create_task(listener(0, self._control_panel.siren))

            _LOGGER.info('Siren changed to %d', self._control_panel.siren.on)

    def _update_output_status(self, outs: List[bool]):
        for i in range(self._model.n_outputs):
            out_number: Id = i + 1
            out = self._control_panel.outputs[out_number]

            if out.on != outs[i]:
                out.on = outs[i]

                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(out_number, out))

                _LOGGER.info('The output %d changed to %d', out_number, out.on)

    def _update_area_status(self, areas: List[ArmingMode]):

        for i in range(self._model.n_areas):
            area_number: Id = i + 1
            area = self._control_panel.areas[area_number]
            status_changed = False

            if areas[i] is ArmingMode.DISARMED:
                if area.mode is not ArmingMode.DISARMED:
                    area.mode = ArmingMode.DISARMED
                    status_changed = True
            elif areas[i] is ArmingMode.ARMED_AWAY:
                if area.mode is not ArmingMode.ARMED_AWAY:
                    status_changed = True
                    area.mode = ArmingMode.ARMED_AWAY
            elif areas[i] is not ArmingMode.ARMED_STAY:
                if area.mode is not ArmingMode.ARMED_STAY:
                    status_changed = True
                    area.mode = ArmingMode.ARMED_STAY

            if status_changed:
                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(area_number, area))

                _LOGGER.info(
                    'Status of Area %d changed to %s', area_number, area.mode
                )

    def _update_time(self, time: Time):
        if self._control_panel.time_utc != time:
            self._control_panel.time_utc = Time(
                hour=time.hour, minute=time.minute
            )

            for listener in self._control_panel_listeners:
                asyncio.create_task(listener(0, self._control_panel.time_utc))

            _LOGGER.info('Time updated %s', self._control_panel.time_utc)
