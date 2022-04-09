import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union
from asyncio import AbstractEventLoop
from aioretry import RetryInfo, retry

from bosch.control_panel.cc880p.models import Area, AreaListener, ArmingMode, Id, Output, SirenListener, Zone, ZoneListener
from bosch.utils.bytes_to_str import to_hex

_LOGGER = logging.getLogger(__name__)

class ControlPanel:
    """Class representing the alarm object
    """

    def __init__(
        self,
        ip: str,
        port: str,
        loop: AbstractEventLoop = asyncio.get_event_loop(),
        number_of_zones: int = 16,
        # number_of_areas: int = 4,
        number_of_areas: int = 1,
        # number_of_outputs: int = 6
        number_of_outputs: int = 1,
        get_status_period_s: float = 2.0

    ):
        """Initialize the Control Panel object to interface through TCP

        Args:
            ip (str):
                IP of the control panel
            port (str):
                Port of the control panel
            loop (AbstractEventLoop, optional):
                Event Loop. Defaults to asyncio.get_event_loop().
            number_of_zones (int, optional):
                Number of zones being used. Defaults to 16.
            number_of_areas (int, optional):
                Number of areas being used. Defaults to 1.
            number_of_outputs (int, optional):
                Number of outputs being used. Defaults to 1.
            get_status_period_s (float, optional):
                Period (in seconds) in which the retrival of the alarm status
                should be performed. Defaults to 2.0.
        """

        # Main event loop
        self._loop = loop

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

        # Dictionary of all the zones
        self._zones: Dict[Id, Zone] = {}
        # Dictionary of all the areas
        self._areas: Dict[Id, Area] = {}
        # Dictionary of all the outputs
        self._outputs: Dict[Id, Output] = {}
        # State of the control panel siren
        self._siren = False

        # Streamreader
        self._reader: Optional[asyncio.StreamReader] = None
        # Streamwriter
        self._writer: Optional[asyncio.StreamWriter] = None

        # Keep track of periodic tasks that need to be stopped if the
        # service is stopped
        self._tasks: List[asyncio.Task] = []
        # Lock
        self._lock = asyncio.Lock()

        # Listeners to be called whenever a zone state is changed
        self._zone_listeners: Dict[Id, List[ZoneListener]] = {}
        # Listeners to be called whenever an area state is changed
        self._area_listeners: Dict[Id, List[AreaListener]] = {}
        # Listeners to be called whenever the siren state is changed
        self._siren_listeners: List[SirenListener] = []

        # Create and initialize the outputs        
        self._create_outputs()
        # Create and initialize the areas
        self._create_areas()
        # Create and initialize th zones
        self._create_zones()


    async def start(self) -> bool:
        """Establish the connection to the control panel
        """

        # Open the connection to the control pannel
        await self._open_connection()
        # Create the task that requests the status periodically
        self._tasks.append(self._loop.create_task(self._get_status_task()))

        return True

    async def stop(self) -> bool:
        """Stops the connection to the control panel
        """

        # Cancels all the permanent tasks
        for task in self._tasks:
            task.cancel()

        return True

    def add_zone_listener(self, zone_number: int, listener: ZoneListener):
        """Add a listener function to listen for zone state changes
        """

        if zone_number in set(self._zones.keys()):
            if zone_number not in self._zone_listeners:
                self._zone_listeners[zone_number] = []
            self._zone_listeners[zone_number].append(listener)

    def add_area_listener(self, area_number: int, listener: AreaListener):
        """Add a listener function to listen for are state changes
        """

        if area_number in set(self._areas.keys()):
            if area_number not in self._area_listeners:
                self._area_listeners[area_number] = []
            self._area_listeners[area_number].append(listener)

    def add_siren_listener(self, listener: SirenListener):
        """Add a listener function to listen for siren state changes
        """

        self._siren_listeners.append(listener)

    async def send_keys(self, keys: Union[str, List[str]], update: bool = False):
        """Simulates a keypad, allowing sending multiple keys
        """

        keys_list: List[str] = list(keys)

        new_keys: bytes = bytes([])

        for k in keys_list:
            if k.isdigit() and int(k) in range(0, 10):
                new_keys += bytes([int(k)])
            elif k == "*":
                new_keys += bytes([0x1B])
            elif k == "#":
                new_keys += bytes([0x1A])
            else:
                _LOGGER.error("Unrecognized key %s", k)
                return

        cmds = []
        max_keys = 1

        for i in range(0, len(new_keys), max_keys):
            cmds.append(new_keys[i : i + max_keys])

        async with self._lock:
            for cmd in cmds:
                current_zone = bytes([1])
                n_keys = bytes([len(cmd)])
                _bytes = bytes.fromhex("0C00000000000000000000")
                _bytes = (
                    _bytes[0:1]
                    + cmd
                    + _bytes[1 + len(cmd) : 8]
                    + current_zone
                    + n_keys
                    + bytes([await self._get_crc(cmd)])
                )
                await self._send_command(_bytes)

            if update:
                await self.get_status_cmd()

    @property
    def zones(self) -> Dict[Id, Zone]:
        """Property that returns the list of zones available
        """

        return self._zones

    @property
    def areas(self) -> Dict[Id, Area]:
        """Property that return the list of areas supported by the alarm
        """

        return self._areas

    @property
    def siren(self) -> bool:
        """Property that return the siren status
        """

        return self._siren

    async def _open_connection(self):
        """Opens the stream connection to the alarm
        """

        if self._writer:
            self._writer.close()

        self._reader, self._writer = await asyncio.open_connection(self._ip, self._port)

    def _create_zones(self):
        """Create and initialize all the zone objects
        """

        for i in range(self._number_of_zones):
            zone = Zone(i + 1)
            self._zones[zone.number] = zone

    def _create_areas(self):
        """Create and initialize all the area objects
        """

        for i in range(self._number_of_areas):
            area = Area(i + 1)
            self._areas[area.number] = area

    def _create_outputs(self):
        """Create and initialize all the output objects
        """

        for i in range(self._number_of_outputs):
            output = Output(i + 1)
            self._outputs[output.number] = output

    @staticmethod
    def _retry_policy(info: RetryInfo) -> Tuple[bool, int]:
        """Retry policy called whenever there's a failure on communication with
        the control panel

        Args:
            info (RetryInfo): The object needed for the retry policy

        Returns:
            Tuple[bool, int]: Tuple with the boolean indicating whether the retry should
            be forgiven, and the timeout for the next retry otherwise
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

    @retry(retry_policy="_retry_policy", before_retry="_before_retry")
    async def _send(self, message: bytes) -> bytes:
        """Sends a binary stream to the control panel and waits for its response

        Args:
            message (bytes): Message to send to the control panel

        Returns:
            bytes: Response of the message sent to the control panel
        """

        # Ensure a clean buffer
        self._reader._buffer.clear()

        # Send the command
        self._writer.write(message)
        await self._writer.drain()

        # Wait for a response
        return await asyncio.wait_for(self._reader.read(32), timeout=3)

    async def _send_command(self, message: bytes) -> Optional[bytes]:
        """Sends a command to the alarm and returns its response

        Args:
            message (bytes): Message to send to the control panel

        Returns:
            bytes: Response of the message sent to the control panel or None otherwise
        """

        resp = None

        try:
            resp = await self._send(message)
        except asyncio.exceptions.TimeoutError:
            _LOGGER.warning("Message not received on time")
        except asyncio.IncompleteReadError as ex:
            _LOGGER.warning("Message not received. Reason: %s", ex)
        except ConnectionResetError:
            _LOGGER.warning("Connection reset by peer")
            await self._open_connection()
        except BaseException as ex:
            _LOGGER.warning("Unexpected Error: %s", ex)

        return resp

    async def _get_status_task(self):
        while True:
            _LOGGER.debug("Getting Status")
            async with self._lock:
                await self.get_status_cmd()
            await asyncio.sleep(self._get_status_period)

    async def get_status_cmd(self):
        """Command to request the status of the alarm
        """

        cmd = bytes([0x01, 0x00, 0x00, 0x00, 0x91, 0x30, 0x19, 0x0F, 0x00, 0x00, 0xF1])
        resp = await self._send_command(cmd)
        if resp:
            _LOGGER.debug("Status Response: %s", resp)
            await self._handle_data(resp)

    async def _handle_data(self, data: bytes):
        _LOGGER.debug("New Data: %s", to_hex(data))

        if self._is_status_msg(data):
            self._handle_status_msg(data)

    @classmethod
    def _is_status_msg(cls, data: bytes):
        return data[:2] == bytes([0x04, 0x34])

    def _handle_status_msg(self, data: bytes):
        self._update_zone_status(data[3:5])
        self._update_siren_status(data[10])
        self._update_area_status(data[9])
        self._update_output_status(data[2])

    def _update_zone_status(self, data: bytes):
        for i in range(self._number_of_zones):
            bit = i % 8
            byte = int(i / 8)
            status = bool(data[byte] & (1 << bit))
            zone = self._zones[i + 1]

            if zone.triggered != status:
                zone.triggered = status

                if zone.number in self._zone_listeners:
                    for listener in self._zone_listeners[zone.number]:
                        if listener:
                            asyncio.create_task(listener(zone))

                _LOGGER.info(
                    "Status of Zone %d changed to %d", zone.number, zone.triggered,
                )

    def _update_siren_status(self, data: int):
        bit = 6
        status = bool(data & (1 << bit))

        if self._siren != status:
            self._siren = status

            for listener in self._siren_listeners:
                if listener:
                    asyncio.create_task(listener(status))

            _LOGGER.info("Status of Siren changed to %d", self._siren)

    def _update_output_status(self, data: int):
        for i in range(self._number_of_outputs):
            bit = i % 8
            status = bool(data & (1 << bit))
            out = self._outputs[i + 1]

            if out.on != status:
                out.on = status
                _LOGGER.info("The output %d changed to %d", out.number, out.on)

    def _update_area_status(self, data: int):

        for i in range(self._number_of_areas):
            away_bit = i % 4
            stay_bit = away_bit + 4
            away_status = bool(data & (1 << away_bit))
            stay_status = bool(data & (1 << stay_bit))
            area = self._areas[i + 1]
            status_chanded = False

            if away_status and stay_status:
                _LOGGER.error(
                    "Both away and stay arming status not possible. Area %d",
                    area.number,
                )
            elif not away_status and not stay_status:
                if area.mode is not ArmingMode.DISARMED:
                    area.mode = ArmingMode.DISARMED
                    status_chanded = True
            elif away_status and area.mode is not ArmingMode.ARMED_AWAY:
                if area.mode is not ArmingMode.ARMED_AWAY:
                    status_chanded = True
                    area.mode = ArmingMode.ARMED_AWAY
            elif stay_status and area.mode is not ArmingMode.ARMED_STAY:
                if area.mode is not ArmingMode.ARMED_STAY:
                    status_chanded = True
                    area.mode = ArmingMode.ARMED_STAY
            if status_chanded:
                if area.number in self._area_listeners:
                    for listener in self._area_listeners[area.number]:
                        if listener:
                            asyncio.create_task(listener(area))
                _LOGGER.info("Status of Area %d changed to %s", area.number, area.mode)

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
