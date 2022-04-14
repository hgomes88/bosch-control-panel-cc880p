import asyncio
import logging

from bosch.control_panel.cc880p.cli.cmds import handle_command
from bosch.control_panel.cc880p.cli.parser import Args
from bosch.control_panel.cc880p.cli.parser import get_args
from bosch.control_panel.cc880p.cp import CP
from bosch.control_panel.cc880p.models import Area
from bosch.control_panel.cc880p.models import ControlPanelModel
from bosch.control_panel.cc880p.models import Id
from bosch.control_panel.cc880p.models import Output
from bosch.control_panel.cc880p.models import Siren
from bosch.control_panel.cc880p.models import Zone
from bosch.utils.bytes_to_str import to_hex

logging.basicConfig(level=logging.WARNING)

prev_data = None


async def data_listener(data: bytes) -> bool:
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


async def cp_listener(id: Id, cp: ControlPanelModel) -> bool:
    if isinstance(cp, Zone):
        print(f'Zone {id} updated: {cp}')
    elif isinstance(cp, Output):
        print(f'Output {id} updated: {cp}')
    elif isinstance(cp, Siren):
        print(f'Siren updated: {cp}')
    elif isinstance(cp, Area):
        print(f'Area {id} updated: {cp}')

    return True


async def run_listen_mode(cp: CP):
    cp.add_data_listener(data_listener)
    cp.add_control_panel_listener(cp_listener)
    while True:
        await asyncio.sleep(1)


async def run_cmd_mode(cp: CP, args):
    await handle_command(cp, args)


async def run(loop):

    args: Args = get_args()

    if args.cmd:
        get_status_period_s = 0
    else:
        get_status_period_s = 2

    cp = CP(
        ip=args.connect,
        port=args.port,
        loop=loop,
        get_status_period_s=get_status_period_s
    )

    await cp.start()

    if args.cmd:
        await run_cmd_mode(cp, args)
    else:
        await run_listen_mode(cp)

    await cp.stop()


def main():
    loop = asyncio.new_event_loop()
    loop.run_until_complete(run(loop))


if __name__ == '__main__':
    main()
