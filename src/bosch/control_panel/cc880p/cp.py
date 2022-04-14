import asyncio
import dataclasses
import logging
from asyncio import AbstractEventLoop
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from aioretry import retry
from aioretry import RetryInfo
from bosch.control_panel.cc880p.models import Area
from bosch.control_panel.cc880p.models import ArmingMode
from bosch.control_panel.cc880p.models import ControlPanel
from bosch.control_panel.cc880p.models import ControlPanelListener
from bosch.control_panel.cc880p.models import DataListener
from bosch.control_panel.cc880p.models import Id
from bosch.control_panel.cc880p.models import Output
from bosch.control_panel.cc880p.models import Siren
from bosch.control_panel.cc880p.models import Time
from bosch.control_panel.cc880p.models import Zone
from bosch.utils.bytes_to_str import to_hex

_LOGGER = logging.getLogger(__name__)


class CP():
    """Class representing the alarm object
    """

    def __init__(
        self,
        ip: str,
        port: str,
        loop: Optional[AbstractEventLoop] = None,
        number_of_zones: int = 16,
        # number_of_areas: int = 4,
        number_of_areas: int = 1,
        number_of_outputs: int = 14,
        get_status_period_s: float = 2.0

    ):
        """Initialize the Control Panel object to interface through TCP

        Args:
            ip (str):
                IP of the control panel
            port (str):
                Port of the control panel
            loop (AbstractEventLoop, optional):
                Event Loop. Defaults None.
            number_of_zones (int, optional):
                Number of zones being used. Defaults to 16.
            number_of_areas (int, optional):
                Number of areas being used. Defaults to 1.
            number_of_outputs (int, optional):
                Number of outputs being used. Defaults to 1.
            get_status_period_s (float, optional):
                Period (in seconds) in which the retrival of the alarm status
                should be performed. If set to 0 or None, then the status is
                not automatically fetch. Defaults to 2.0.
        """

        # Main event loop
        self._loop = loop or asyncio.get_event_loop()

        self._get_status_period = get_status_period_s

        # IP of the control panel
        self._ip = ip
        # Port of the control panel
        self._port = port

        # Number of zones available in the alarm
        self._number_of_zones = number_of_zones
        # Number of areas available in the alarm
        self._number_of_areas = number_of_areas
        # Number of outputs available in the alarm
        self._number_of_outputs = number_of_outputs

        # Streamreader
        self._reader: Optional[asyncio.StreamReader] = None
        # Streamwriter
        self._writer: Optional[asyncio.StreamWriter] = None

        # Keep track of periodic tasks that need to be stopped if the
        # service is stopped
        self._tasks: List[asyncio.Task] = []
        # Lock
        self._lock = asyncio.Lock()

        # Listeners to be called whenever the control panel state is changed
        self._control_panel_listeners: List[ControlPanelListener] = []
        # Listeners to be called whenever the there's new data
        self._data_listeners: List[DataListener] = []

        self._control_panel = ControlPanel(
            # Create and initialize the siren
            siren=self._create_siren(),
            # Create and initialize the outputs
            outputs=self._create_outputs(),
            # Create and initialize the areas
            areas=self._create_areas(),
            # Create and initialize th zones
            zones=self._create_zones(),
            # Create and initialize the time
            time_utc=self._create_time(),
        )

    def __repr__(self):
        return str(self._control_panel)

    @property
    def __dict__(self):
        return dataclasses.asdict(
            self._control_panel,
            dict_factory=self._custom_asdict_factory
        )

    @classmethod
    def _custom_asdict_factory(cls, data):
        def convert_value(obj):
            if isinstance(obj, Enum):
                return obj.name
            return obj

        return {k: convert_value(v) for k, v in data}

    async def start(self) -> bool:
        """Establish the connection to the control panel
        """

        # Open the connection to the control panel
        await self._open_connection()
        # Create the task that requests the status periodically
        if self._get_status_period:
            self._tasks.append(self._loop.create_task(self._get_status_task()))

        return True

    async def stop(self) -> bool:
        """Stops the connection to the control panel
        """

        # Cancels all the permanent tasks
        for task in self._tasks:
            task.cancel()

        return True

    def add_control_panel_listener(self, listener: ControlPanelListener):
        """Add a listener function to listen for any change in the alarm
        """

        self._control_panel_listeners.append(listener)

    def add_data_listener(self, listener: DataListener):
        """Add a listener function to listen for any incoming data
        """

        self._data_listeners.append(listener)

    async def send_keys(
        self,
        keys: Union[str, List[str]],
        update: bool = False
    ):
        """Simulates a keypad, allowing sending multiple keys
        """

        keys_list: List[str] = list(keys)

        new_keys: bytes = bytes([])

        for k in keys_list:
            if k.isdigit() and int(k) in range(0, 10):
                new_keys += bytes([int(k)])
            elif k == '*':
                new_keys += bytes([0x1B])
            elif k == '#':
                new_keys += bytes([0x1A])
            else:
                _LOGGER.error('Unrecognized key %s', k)
                return

        cmds = []
        max_keys = 1

        for i in range(0, len(new_keys), max_keys):
            cmds.append(new_keys[i: i + max_keys])

        for cmd in cmds:
            current_zone = bytes([1])
            n_keys = bytes([len(cmd)])
            _bytes = bytes.fromhex('0C00000000000000000000')
            _bytes = (
                _bytes[0:1]
                + cmd
                + _bytes[1 + len(cmd): 8]
                + current_zone
                + n_keys
                + bytes([await self._get_crc(cmd)])
            )
            await self._send_command(_bytes)

        if update:
            await self.get_status_cmd()

    @classmethod
    def _supports_set_output(cls, id: Id):
        if 0 < id <= 4:
            return True
        return False

    @classmethod
    def _get_output_bytes(cls, id: Id, on: bool = True) -> bytes:
        """Gets the bytes that represents the command to enable/disable a
        certain output

            # 0e 03 00 00 00 00 00 00 00 00 1a 	Enable Output 1
            # 0e 04 00 00 00 00 00 00 00 00 1a 	Disable Output 1
            # 0e 03 01 00 00 00 00 00 00 00 1a 	Enable Output 2
            # 0e 04 01 00 00 00 00 00 00 00 1a 	Disable Output 2
            # 0e 03 02 00 00 00 00 00 00 00 1b 	Enable Output 3
            # 0e 04 02 00 00 00 00 00 00 00 1b 	Disable Output 3
            # 0e 03 03 00 00 00 00 00 00 00 1d 	Enable Output 4
            # 0e 04 03 00 00 00 00 00 00 00 1d 	Disable Output 4
            # 0e 03 04 00 00 00 00 00 00 00 1d 	Enable Output 5
            # 0e 04 04 00 00 00 00 00 00 00 1d 	Disable Output 5

        Args:
            id (Id): Output Id
            on (bool): whether is to enable the the output. Defaults to True.

        Raises:
            ValueError: If the output selected is not supported to be changed

        Returns:
            bytes: The bytes representation of the command
        """

        idx = id - 1
        if id in [1, 2]:
            if on:
                ret = bytes([0x0e, 0x03, idx, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x1a])
            else:
                ret = bytes([0x0e, 0x04, idx, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x1a])
        elif id == 3:
            if on:
                ret = bytes([0x0e, 0x03, idx, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x1b])
            else:
                ret = bytes([0x0e, 0x04, idx, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x1b])
        elif id in [4, 5]:
            if on:
                ret = bytes([0x0e, 0x03, idx, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x1d])
            else:
                ret = bytes([0x0e, 0x04, idx, 0x00, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x1d])
        else:
            raise ValueError(f'The output with the id {id} is not supported')

        return ret

    async def set_output(self, id: Id, on: bool):
        try:
            if id not in self.control_panel.outputs:
                raise ValueError(f"The output with {id} doesn't exist")

            if self._control_panel.outputs[id].on != on:
                await self._send_command(self._get_output_bytes(id, on))
        except Exception as ex:
            _LOGGER.error(f'Error setting the output: {ex}')

    async def set_arming(self, id: Id = 1, arm: bool = False):
        if arm and self._control_panel.areas[id].mode == ArmingMode.DISARMED:
            # Arm
            await self._send_command(
                bytes([
                    0x0e, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x17
                ])
            )
        elif not arm and \
                self._control_panel.areas[id].mode != ArmingMode.DISARMED:
            # Disarm
            await self._send_command(
                bytes([
                    0x0e, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x18
                ])
            )

    async def set_siren(self, on: bool = False):
        if on and self._control_panel.siren.on != on:
            # Switch on the siren
            await self._send_command(
                bytes([
                    0x0e, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x1C
                ])
            )
        elif not on and self._control_panel.siren.on != on:
            # Switch of the siren
            await self._send_command(
                bytes([
                    0x0e, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x1D
                ])
            )

    @property
    def control_panel(self) -> ControlPanel:
        """Property that returns the control panel object
        """

        return self._control_panel

    async def _open_connection(self):
        """Opens the stream connection to the alarm
        """

        if self._writer:
            self._writer.close()

        self._reader, self._writer = await asyncio.open_connection(
            self._ip,
            self._port
        )

    def _create_siren(self) -> Siren:
        """Create and initialize the siren object
        """

        return Siren()

    def _create_areas(self) -> Dict[Id, Area]:
        """Create and initialize all the area objects
        """

        return {i + 1: Area() for i in range(self._number_of_areas)}

    def _create_zones(self) -> Dict[Id, Zone]:
        """Create and initialize all the zone objects
        """

        return {i + 1: Zone() for i in range(self._number_of_zones)}

    def _create_outputs(self) -> Dict[Id, Output]:
        """Create and initialize all the output objects
        """

        return {i + 1: Output() for i in range(self._number_of_outputs)}

    def _create_time(self) -> Time:
        """Create and initialize the siren object
        """

        return Time()

    @staticmethod
    def _retry_policy(info: RetryInfo) -> Tuple[bool, int]:
        """Retry policy called whenever there's a failure on communication with
        the control panel

        Args:
            info (RetryInfo):
                The object needed for the retry policy

        Returns:
            Tuple[bool, int]:
                Tuple with the boolean indicating whether the retry should be
                forgiven, and the timeout for the next retry otherwise
        """

        if (
            isinstance(
                info.exception,
                (asyncio.exceptions.TimeoutError, ConnectionResetError)
            )
            and info.fails <= 2
        ):
            # Do not forgive, retry in 2 seconds
            return False, 2
        # Forgive
        return True, 0

    async def _before_retry(self, info: RetryInfo):
        """Callback called before every retry

        Args:
            info (RetryInfo): The object needed for the retry policy
        """

        # Reconnect
        if info.fails >= 2:
            await self._open_connection()

    @retry(retry_policy='_retry_policy', before_retry='_before_retry')
    async def _send(self, message: bytes) -> bytes:
        """Sends a binary stream to the control panel and waits for its response

        Args:
            message (bytes): Message to send to the control panel

        Returns:
            bytes: Response of the message sent to the control panel
        """

        if self._reader and self._writer:
            # # Ensure a clean buffer
            self._reader._buffer.clear()  # type: ignore

            # Send the command
            self._writer.write(message)
            await self._writer.drain()

            # Wait for a response
            return await asyncio.wait_for(self._reader.read(32), timeout=3)
        else:
            raise RuntimeError('Stream not initialized')

    async def _send_command(self, message: bytes) -> Optional[bytes]:
        """Sends a command to the alarm and returns its response

        Args:
            message (bytes):
                Message to send to the control panel

        Returns:
            bytes:
                Response of the message sent to the control panel or None
                otherwise
        """

        resp = None

        async with self._lock:
            try:
                resp = await self._send(message)
            except asyncio.exceptions.TimeoutError:
                _LOGGER.warning('Message not received on time')
            except asyncio.IncompleteReadError as ex:
                _LOGGER.warning('Message not received. Reason: %s', ex)
            except ConnectionResetError:
                _LOGGER.warning('Connection reset by peer')
                await self._open_connection()
            except BaseException as ex:
                _LOGGER.warning('Unexpected Error: %s', ex)

        return resp

    async def _get_status_task(self):
        while True:
            _LOGGER.debug('Getting Status')
            try:
                await self.get_status_cmd()
            except Exception as ex:
                _LOGGER.error(f'Error during getting the status {ex}')
            await asyncio.sleep(self._get_status_period)

    async def get_status_cmd(self):
        """Command to request the status of the alarm
        """

        cmd = bytes([0x01, 0x00, 0x00, 0x00, 0x91,
                    0x30, 0x19, 0x0F, 0x00, 0x00, 0xF1])
        resp = await self._send_command(cmd)
        if resp:
            _LOGGER.debug('Status Response: %s', resp)
            await self._handle_data(resp)

    async def _handle_data(self, data: bytes):
        _LOGGER.debug('New Data: %s', to_hex(data))

        if self._is_status_msg(data):
            self._handle_status_msg(data)

        for listener in self._data_listeners:
            asyncio.create_task(listener(data))

    @classmethod
    def _is_status_msg(cls, data: bytes):
        frame_size = 13

        if data[0] != 0x04:
            return False

        if len(data) != frame_size:
            raise ValueError(
                f'The size of the frame should be {frame_size}'
                f' but is {len(data)}'
            )

        return True

    def _handle_status_msg(self, data: bytes):
        self._update_siren_status(data[10])
        self._update_output_status(data[1:3])
        self._update_area_status(data[9])
        self._update_zone_status(data[3:5])
        self.update_zone_enabled(data[5:7])
        self._update_time(data[10:12])

    def _update_zone_status(self, data: bytes):
        for i in range(self._number_of_zones):
            bit = i % 8
            byte = int(i / 8)
            status = bool(data[byte] & (1 << bit))
            zone_number: Id = i + 1
            zone = self._control_panel.zones[zone_number]

            if zone.triggered != status:
                zone.triggered = status

                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(zone_number, zone))

                _LOGGER.info(
                    'Status of Zone %d changed to %d',
                    zone_number,
                    zone.triggered
                )

    def update_zone_enabled(self, data: bytes):

        area = list(self._control_panel.areas.values())[0]
        if area.mode == ArmingMode.ARMED_AWAY:
            status = True
        elif area.mode == ArmingMode.DISARMED:
            status = False

        for i in range(self._number_of_zones):
            bit = i % 8
            byte = int(i / 8)
            if area.mode == ArmingMode.ARMED_STAY:
                status = bool(data[byte] & (1 << bit))
            zone_number = i + 1
            zone = self._control_panel.zones[zone_number]

            if zone.enabled != status:
                zone.enabled = status

                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(id, zone))

                _LOGGER.info(
                    'Zone enabling of Zone %d changed to %d',
                    zone_number,
                    zone.enabled
                )

    def _update_siren_status(self, data: int):
        bit = 6
        status = bool(data & (1 << bit))

        if self._control_panel.siren.on != status:
            self._control_panel.siren.on = status

            for listener in self._control_panel_listeners:
                asyncio.create_task(listener(0, self._control_panel.siren))

            _LOGGER.info('Siren changed to %d', self._control_panel.siren)

    def _update_output_status(self, data: bytes):
        for i in range(self._number_of_outputs):
            bit = i % 8
            byte = len(data) - int(i / 8) - 1
            status = bool(data[byte] & (1 << bit))
            id: Id = i + 1
            out = self._control_panel.outputs[id]

            if out.on != status:
                out.on = status

                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(id, out))

                _LOGGER.info('The output %d changed to %d', id, out.on)

    def _update_area_status(self, data: int):

        for i in range(self._number_of_areas):
            away_bit = i % 4
            stay_bit = away_bit + 4
            away_status = bool(data & (1 << away_bit))
            stay_status = bool(data & (1 << stay_bit))
            area_number: Id = i + 1
            area = self._control_panel.areas[area_number]
            status_changed = False

            if away_status and stay_status:
                _LOGGER.error(
                    'Both away and stay arming status not possible. Area %d',
                    area_number,
                )
            elif not away_status and not stay_status:
                if area.mode is not ArmingMode.DISARMED:
                    area.mode = ArmingMode.DISARMED
                    status_changed = True
            elif away_status and area.mode is not ArmingMode.ARMED_AWAY:
                if area.mode is not ArmingMode.ARMED_AWAY:
                    status_changed = True
                    area.mode = ArmingMode.ARMED_AWAY
            elif stay_status and area.mode is not ArmingMode.ARMED_STAY:
                if area.mode is not ArmingMode.ARMED_STAY:
                    status_changed = True
                    area.mode = ArmingMode.ARMED_STAY
            if status_changed:

                for listener in self._control_panel_listeners:
                    asyncio.create_task(listener(area_number, area))

                _LOGGER.info(
                    'Status of Area %d changed to %s',
                    area_number,
                    area.mode)

    def _update_time(self, data: bytes):

        # Hours
        hours = data[0] & 0x1F  # Only the first 5 bits matters (0h-23h)
        # Minutes
        minutes = data[1] & 0x3F  # Only the first 6 bits matters (0m-59m)
        # Time
        time: Time = Time(hour=hours, minute=minutes)

        if self._control_panel.time_utc != time:
            self._control_panel.time_utc = time

            for listener in self._control_panel_listeners:
                asyncio.create_task(listener(0, self._control_panel.time_utc))

            _LOGGER.info('Time updated %s', self._control_panel.time_utc)

    async def _get_crc(self, data: bytes):

        # TODO: For now we can have only static CRC
        if len(data) == 1:
            if data[0] in [0x00, 0x01]:
                return 0x16
            if data[0] in [0x02]:
                return 0x17
            if data[0] in [0x03, 0x04]:
                return 0x19
            if data[0] in [0x05]:
                return 0x1B
            if data[0] in [0x06, 0x07]:
                return 0x1C
            if data[0] in [0x08]:
                return 0x1D
            if data[0] in [0x09]:
                return 0x1F
            if data[0] in [0x1A]:
                return 0x2F
            if data[0] in [0x1B]:
                return 0x31

        return 0
