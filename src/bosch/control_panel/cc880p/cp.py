"""Control Panel."""
import asyncio
import dataclasses
import datetime
import logging
from asyncio import AbstractEventLoop
from asyncio import Task
from asyncio.exceptions import CancelledError
from enum import Enum
from typing import List
from typing import Optional
from typing import Union

from bosch.control_panel.cc880p.models import errors
from bosch.control_panel.cc880p.models.constants import Id
from bosch.control_panel.cc880p.models.constants import MAX_KEYS
from bosch.control_panel.cc880p.models.constants import MAX_POLL_PERIOD_S
from bosch.control_panel.cc880p.models.cp import ArmingMode
from bosch.control_panel.cc880p.models.cp import ControlPanel
from bosch.control_panel.cc880p.models.cp import CpModel
from bosch.control_panel.cc880p.models.listener import BaseControlPanelListener
from bosch.control_panel.cc880p.models.listener import EventProducer
from bosch.control_panel.cc880p.models.requests import KeysRequest
from bosch.control_panel.cc880p.models.requests import Request
from bosch.control_panel.cc880p.models.requests import SetArmingRequest
from bosch.control_panel.cc880p.models.requests import SetOutRequest
from bosch.control_panel.cc880p.models.requests import SetSirenRequest
from bosch.control_panel.cc880p.models.requests import SetTimeRequest
from bosch.control_panel.cc880p.models.requests import StatusRequest
from bosch.control_panel.cc880p.models.responses import Response
from bosch.control_panel.cc880p.models.responses import StatusResponse

_LOGGER = logging.getLogger(__name__)


class CP:
    """Alarm control panel object representation."""

    ###########################################################################
    # Init
    ###########################################################################

    def __init__(
        self,
        ip: str,
        port: int,
        model: CpModel,
        installer_code: str = None,
        poll_period: float = 1.0,
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

        self._init_poll_period = poll_period
        self._poll_period = self._init_poll_period

        # Streamreader
        self._reader: Optional[asyncio.StreamReader] = None
        # Streamwriter
        self._writer: Optional[asyncio.StreamWriter] = None
        # Connected
        self._connected: bool = False
        # Reconnection task
        self._conn_task: Optional[Task] = None

        # Lock
        self._lock = asyncio.Lock()

        self._listeners: List[BaseControlPanelListener] = []

        self._control_panel = ControlPanel.build(self._model)

        self._evt = EventProducer(self._control_panel)

        self._update_last_request()

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

    @property
    def connected(self) -> bool:
        """Report whether the connection to the alarm is established."""
        return self._connected

    async def _set_connected(self, connected=True):
        if connected != self._connected:
            self._connected = connected
            self.control_panel.availability.available = self._connected
            await self._evt.notify_availability_changed()

    async def start(self) -> 'CP':
        """Establish the connection to the control panel."""
        await self._connect()
        return self

    async def stop(self) -> 'CP':
        """Stop the connection to the control panel."""
        await self._disconnect()
        return self

    ###########################################################################
    # Connection
    ###########################################################################

    async def _connect(self):
        connected = False
        _LOGGER.info('Connecting')
        try:
            # Start the connection
            await self._open_connection()
            # Ensure the connection is established by requesting for its status
            await self._get_status()
            # Set the connection state to connected
            connected = True
        except errors.Error as exc:
            _LOGGER.error(f'Error: {repr(exc)}')
        except BaseException:
            _LOGGER.exception('Unknown error:')
        else:
            _LOGGER.info('Connected')
        finally:
            # Always update the connection state
            await self._set_connected(connected)
            # Always create the connection task if not created yet
            await self._create_connection_task()

    async def _open_connection(self):
        """Open the stream connection to the alarm."""
        async with self._lock:
            try:
                self._reader, self._writer = await asyncio.open_connection(
                    self._ip,
                    self._port
                )
            except ConnectionRefusedError as exc:
                raise ConnectionError from exc
            except OSError as exc:
                if exc.errno == 113:
                    raise errors.ConnectionError from exc
                else:
                    raise

    async def _create_connection_task(self):
        if not self._conn_task:
            self._conn_task = asyncio.create_task(self._connection_task())

    async def _disconnect(self):
        # Cancel any connection related task
        await self._cancel_connection_task()
        # Ensure any previous connection is closed
        await self._close_connection()
        # Set the connection state to disconnected
        await self._set_connected(False)

    async def _cancel_connection_task(self):
        if self._conn_task:
            self._conn_task.cancel()
            self._conn_task = None

    async def _close_connection(self):
        async with self._lock:
            if self._reader:
                if not self._reader.at_eof():
                    self._reader.feed_eof()
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()

            self._reader = None
            self._writer = None

    async def _connection_task(self):
        period = self._retry_period(init=True)
        while True:
            try:
                if not self.connected:
                    _LOGGER.info('Reconnecting')
                    await self._close_connection()
                    await self._connect()
                    if self.connected:
                        _LOGGER.info('Reconnected')
                        period = self._retry_period(init=True)
                    else:
                        period = self._retry_period()
                        _LOGGER.error(
                            f'Reconnection failed. Retrying in {period} '
                            'seconds.'
                        )
                else:
                    # Ask for status to check if connection with the control
                    # panel is still available
                    now = datetime.datetime.now()
                    if abs(
                        now - self.last_request_time
                    ).total_seconds() >= self._init_poll_period:
                        _LOGGER.debug('Polling Status')
                        await self.get_status()
            except CancelledError:
                raise
            except errors.Error as exc:
                _LOGGER.error(f'Error: {repr(exc)}')
                self._retry_period()
            except BaseException:
                _LOGGER.exception('Unknown error:')
                self._retry_period()

            try:
                await asyncio.sleep(period)
            except CancelledError:
                raise

    def _retry_period(self, init=False):
        if init:
            self._poll_period = self._init_poll_period
        else:
            self._poll_period = self._poll_period * 2

        if self._poll_period > MAX_POLL_PERIOD_S:
            self._poll_period = MAX_POLL_PERIOD_S

        return self._poll_period

    ###########################################################################
    # Listeners
    ###########################################################################

    def add_listener(self, listener: BaseControlPanelListener):
        """Add a listener to listen for change events."""
        self._evt.add_listener(listener)

    def remove_listener(self, listener: BaseControlPanelListener):
        """Remove a listener."""
        self._evt.remove_listener(listener)

    def clear_listeners(self):
        """Remove all the listeners."""
        self._evt.clear_listeners()

    ###########################################################################
    # Commands
    ###########################################################################

    def _command(func):
        async def wrapper(self, *args, **kwargs):
            if self.connected:
                return await func(self, *args, **kwargs)
            raise errors.ConnectionError('Not connected')
        return wrapper

    @_command  # type: ignore
    async def get_status(self):
        """Get the control panel status."""
        return await self._get_status()

    async def _get_status(self):
        """Get the control panel status."""
        status_request = StatusRequest(installer_code=self._installer_code)
        status_response = await self._send_request(
            status_request,
            StatusResponse
        )
        await self._handle_status_msg(status_response)
        return status_response

    @_command  # type: ignore
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
            status_response = await self._send_request(request, StatusResponse)

        await self._handle_status_msg(status_response)

    def _encode_keys(self, keys: Union[str, List[str]]) -> bytes:
        return bytes(self._encode_key(key) for key in list(keys))

    def _encode_key(self, key: str) -> int:
        # Is a number between 0 and 9
        if key.isdigit() and int(key) in range(0, 10):
            return int(key)
        elif key == '*':
            return 0x1B
        elif key == '#':
            return 0x1A
        else:
            msg = 'Unrecognized key %s', key
            _LOGGER.error(msg)
            raise errors.ValueError(msg)

    @_command  # type: ignore
    async def set_output(self, id: Id, on: bool) -> bool:
        """Set output."""
        if id not in self.control_panel.outputs:
            raise errors.ValueError(f"The output with {id} doesn't exist")

        if self._control_panel.outputs[id].on != on:
            request = SetOutRequest(id, on)
            status_response = await self._send_request(request, StatusResponse)
            await self._handle_status_msg(status_response)

        return self._control_panel.outputs[id].on

    @_command  # type: ignore
    async def set_arming(
        self,
        id: Id = 1,
        arm: bool = False
    ) -> bool:
        """Set arming."""
        request = None

        if arm and self._control_panel.areas[id].mode == ArmingMode.DISARMED:
            request = SetArmingRequest(id, arm)

        elif not arm and \
                self._control_panel.areas[id].mode != ArmingMode.DISARMED:
            request = SetArmingRequest(id, arm)

        if request:
            status_response = await self._send_request(request, StatusResponse)
            await self._handle_status_msg(status_response)

        # Arming takes some time, so request again for the status
        await self.get_status()

        return self._control_panel.areas[id].mode != ArmingMode.DISARMED

    @_command  # type: ignore
    async def set_siren(self, on: bool = False):
        """Set siren on or off.."""
        request = None
        if on and self._control_panel.siren.on != on:
            # Switch on the siren
            request = SetSirenRequest(on)
        elif not on and self._control_panel.siren.on != on:
            # Switch of the siren
            request = SetSirenRequest(on)

        if request:
            status_response = await self._send_request(request, StatusResponse)
            await self._handle_status_msg(status_response)

        return self._control_panel.siren.on

    @_command  # type: ignore
    async def set_time(self, time: datetime.datetime = None) -> datetime.time:
        """Set time."""
        # Set the time in the alarm
        status_response = await self._send_request(
            SetTimeRequest(time),
            StatusResponse
        )
        await self._handle_status_msg(status_response)
        return self._control_panel.time.time

    ###########################################################################
    # Write/Read
    ###########################################################################

    async def _send_request(
        self,
        request: Request,
        response: Optional[Response]
    ) -> Union[Response, Optional[bytes]]:
        """Send a new request."""
        try:
            resp = await self._send(
                message=request.encode(),
                resp_size=response.size if response else 0,
                timeout=3
            )
            await self._evt.notify_data(resp)
        except BaseException:
            await self._set_connected(False)
            raise
        finally:
            self._update_last_request()

        if response and self._valid_response(resp, response):
            resp = response.decode(resp, self._model)
        else:
            raise errors.MessageError(
                'Invalid response. Expected to be a frame of type '
                f'{type(response)} but the message is {resp!r}'
            )
        return resp

    def _valid_response(
            self,
            raw_resp: Optional[bytes],
            response: Response) -> bool:
        valid = False

        if raw_resp and len(raw_resp) == response.size:
            if bytes([raw_resp[0]]) == bytes.fromhex(response.code):
                valid = True

        return valid

    async def _send(
        self,
        message: bytes,
        resp_size: int = 0,
        timeout=3
    ) -> Optional[bytes]:
        """Send a binary stream to the control panel and waits for its response.

        Args:
            message (bytes): Message to send to the control panel

        Returns:
            bytes: Response of the message sent to the control panel
        """
        if not self._writer:
            raise errors.ConnectionError('Writer is not open')
        elif not self._reader:
            raise errors.ConnectionError('Reader is not open')

        async with self._lock:
            # Ensure a clean buffer
            self._reader._buffer.clear()  # type: ignore
            # Send the command
            await self._write(message)
            # Wait for a response
            return await self._read(resp_size, timeout)

    async def _write(self, message: bytes):
        if self._writer:
            try:
                self._writer.write(message)
                await self._writer.drain()
                return
            except ConnectionRefusedError as exc:
                raise errors.ConnectionError from exc
            except OSError as exc:
                if exc.errno == 113:
                    raise errors.ConnectionError from exc
                else:
                    raise

        raise errors.ConnectionError('Writer is not open')

    async def _read(
        self,
        read_size: int = 0,
        timeout: float = 3
    ) -> Optional[bytes]:

        data: Optional[bytes] = None

        if self._reader:
            if not self._reader.at_eof():
                try:
                    if read_size:
                        data = await asyncio.wait_for(
                            self._reader.readexactly(read_size),
                            timeout=timeout
                        )
                    else:
                        data = await asyncio.wait_for(
                            self._reader.read(32), timeout=timeout
                        )
                    return data
                except asyncio.exceptions.TimeoutError as exc:
                    raise errors.TimeoutError from exc
                except asyncio.exceptions.IncompleteReadError as exc:
                    raise errors.MessageError from exc
                except ConnectionRefusedError as exc:
                    raise errors.ConnectionError from exc
                except OSError as exc:
                    if exc.errno == 113:
                        raise errors.ConnectionError from exc
                    else:
                        raise
            else:
                raise errors.MessageError('EOF')

        raise errors.ConnectionError('Reader is not open')

    def _update_last_request(self):
        self._last_request = datetime.datetime.now()

    @property
    def last_request_time(self) -> datetime.datetime:
        """Get the last request time."""
        return self._last_request

    ###########################################################################
    # Response Handlers
    ###########################################################################

    async def _handle_status_msg(self, status: StatusResponse):
        await self._update_siren_status(status.siren)
        await self._update_output_status(status.outs)
        await self._update_area_status(status.areas)
        await self._update_zone_status(status.zones)
        await self.update_zone_enabled(status.zones_en)
        await self._update_time(status.time)

    async def _update_zone_status(self, zones: List[bool]):
        for i in range(self._model.n_zones):
            zone_number: Id = i + 1
            zone = self._control_panel.zones[zone_number]
            if zone.triggered != zones[i]:
                zone.triggered = zones[i]
                await self._evt.notify_zone_trigger_changed(zone_number)
                _LOGGER.info(
                    'Status of Zone %d changed to %d',
                    zone_number,
                    zone.triggered
                )

    async def update_zone_enabled(self, zones_en: List[bool]):
        """Update zone enabled."""
        for i in range(self._model.n_zones):
            zone_number = i + 1
            zone = self._control_panel.zones[zone_number]
            if zone.enabled != zones_en[i]:
                zone.enabled = zones_en[i]
                await self._evt.notify_zone_enabling_changed(zone_number)
                _LOGGER.info(
                    'Zone enabling of Zone %d changed to %d',
                    zone_number,
                    zone.enabled
                )

    async def _update_siren_status(self, status: bool):
        if self._control_panel.siren.on != status:
            self._control_panel.siren.on = status
            await self._evt.notify_siren_changed()
            _LOGGER.info('Siren changed to %d', self._control_panel.siren.on)

    async def _update_output_status(self, outs: List[bool]):
        for i in range(self._model.n_outputs):
            out_number: Id = i + 1
            out = self._control_panel.outputs[out_number]
            if out.on != outs[i]:
                out.on = outs[i]
                await self._evt.notify_output_changed(out_number)
                _LOGGER.info('The output %d changed to %d', out_number, out.on)

    async def _update_area_status(self, areas: List[ArmingMode]):
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
                await self._evt.notify_area_changed()
                _LOGGER.info(
                    'Status of Area %d changed to %s', area_number, area.mode
                )

    async def _update_time(self, time: datetime.time):
        if self._control_panel.time.time != time:
            self._control_panel.time.time = time
            await self._evt.notify_time_changed()
            _LOGGER.info('Time updated %s', self._control_panel.time)
