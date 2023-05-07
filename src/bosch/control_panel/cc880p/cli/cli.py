"""Control panel command line interface."""
import asyncio
import logging

from bosch.control_panel.cc880p.cli.cmds import handle_command
from bosch.control_panel.cc880p.cli.parser import Args
from bosch.control_panel.cc880p.cli.parser import get_args
from bosch.control_panel.cc880p.cp import CP
from bosch.control_panel.cc880p.models.cp import Area
from bosch.control_panel.cc880p.models.cp import Availability
from bosch.control_panel.cc880p.models.cp import ControlPanelEntity
from bosch.control_panel.cc880p.models.cp import CpVersion
from bosch.control_panel.cc880p.models.cp import Id
from bosch.control_panel.cc880p.models.cp import Output
from bosch.control_panel.cc880p.models.cp import Siren
from bosch.control_panel.cc880p.models.cp import Zone
from bosch.control_panel.cc880p.utils import to_hex

logging.basicConfig(level=logging.WARNING)

prev_data = None


async def data_listener(data: bytes) -> bool:
    """Listen of any control panel change."""
    global prev_data
    if prev_data and prev_data[:-2] != data[:-2]:
        print('\nDifference:')
        print(f'\tBefore:\t{to_hex(prev_data)}')
        print(f'\tAfter:\t{to_hex(data)}')
    else:
        print('\nNo Changes:')
        print(to_hex(data))
    prev_data = data
    return True


async def cp_listener(id: Id, cp: ControlPanelEntity) -> bool:
    """Control panel listener."""
    if isinstance(cp, Zone):
        print(f'Zone {id} updated: {cp}')
    elif isinstance(cp, Output):
        print(f'Output {id} updated: {cp}')
    elif isinstance(cp, Siren):
        print(f'Siren updated: {cp}')
    elif isinstance(cp, Area):
        print(f'Area {id} updated: {cp}')
    elif isinstance(cp, Availability):
        print(f'Control Panel availability is: {cp}')

    return True


async def run_listen_mode(cp: CP):
    """Run the control panel in listen mode."""
    cp.add_data_listener(data_listener)
    cp.add_control_panel_listener(cp_listener)
    while True:
        await cp.get_status()
        await asyncio.sleep(1)


async def run_cmd_mode(cp: CP, args):
    """Run mode command."""
    await handle_command(cp, args)


async def run(loop):
    """Run the control panel command line."""
    args: Args = get_args()

    cp = CP(
        ip=args.connect,
        port=args.port,
        model=CpVersion.S16_V14.model(),
        installer_code=args.code,
        loop=loop,
    )

    await cp.start()

    if args.cmd:
        await run_cmd_mode(cp, args)
    else:
        await run_listen_mode(cp)

    await cp.stop()


def main():
    """Run main."""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run(loop))


if __name__ == '__main__':
    main()
