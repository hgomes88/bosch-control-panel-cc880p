"""Control panel command line interface."""
import asyncio
import logging

from bosch.control_panel.cc880p.cli.cmds import handle_command
from bosch.control_panel.cc880p.cli.parser import Args
from bosch.control_panel.cc880p.cli.parser import get_args
from bosch.control_panel.cc880p.cp import CP
from bosch.control_panel.cc880p.models.constants import Id
from bosch.control_panel.cc880p.models.cp import Area
from bosch.control_panel.cc880p.models.cp import Availability
from bosch.control_panel.cc880p.models.cp import CpVersion
from bosch.control_panel.cc880p.models.cp import Output
from bosch.control_panel.cc880p.models.cp import Siren
from bosch.control_panel.cc880p.models.cp import Time
from bosch.control_panel.cc880p.models.cp import Zone
from bosch.control_panel.cc880p.models.errors import Error
from bosch.control_panel.cc880p.models.listener import BaseControlPanelListener
from bosch.control_panel.cc880p.utils import to_hex

logging.basicConfig(level=logging.DEBUG)

prev_data = None


class Listener(BaseControlPanelListener):
    """Lister class implementing all events of interest."""

    def __init__(self, cp: CP):
        """Init."""
        self._cp = cp

    async def on_availability_changed(self, entity: Availability):
        """On availability changed."""
        print(f'Control Panel availability is: {entity}')

    async def on_area_changed(self, entity: Area):
        """On area changed."""
        print(f'Area {id} updated: {entity}')

    async def on_siren_changed(self, entity: Siren):
        """On siren changed."""
        print(f'Siren updated: {entity}')

    async def on_zone_changed(self, id: Id, entity: Zone):
        """On zone changed."""
        print(f'Zone {id} updated: {entity}')

    async def on_time_changed(self, entity: Time):
        """On time changed."""
        print('Time changed to:', entity)

    async def on_output_changed(self, id: Id, entity: Output):
        """On output changed."""
        print(f'Output {id} updated: {entity}')

    async def on_data(self, data: bytes):
        """On data changed."""
        global prev_data
        if prev_data and prev_data[:-2] != data[:-2]:
            print('\nDifference:')
            print(f'\tBefore:\t{to_hex(prev_data)}')
            print(f'\tAfter:\t{to_hex(data)}')
        else:
            print('\nNo Changes:')
            print(to_hex(data))
        prev_data = data


async def run_listen_mode(cp: CP):
    """Run the control panel in listen mode."""
    cp.add_listener(Listener(cp))
    while True:
        await asyncio.sleep(1)


async def run_cmd_mode(cp: CP, args):
    """Run mode command."""
    resp = await handle_command(cp, args)
    print('Resp:', resp)


async def run(loop):
    """Run the control panel command line."""
    args: Args = get_args()

    cp = CP(
        ip=args.connect,
        port=args.port,
        model=CpVersion.S16_V14.model(),
        installer_code=args.code,
        poll_period=3,
        loop=loop,
    )

    await cp.start()

    if args.cmd:
        try:
            await run_cmd_mode(cp, args)
        except Error as exc:
            logging.error(f'Error: {repr(exc)}')
        except BaseException:
            logging.exception('Unknown error:')

    else:
        await run_listen_mode(cp)

    await cp.stop()


def main():
    """Run main."""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run(loop))


if __name__ == '__main__':
    main()
