from typing import Any
from typing import List

from bosch.control_panel.cc880p.cli.parser import Args
from bosch.control_panel.cc880p.cli.parser import Commands
from bosch.control_panel.cc880p.cp import CP


def cmd(cp: CP, obj: Any = None):
    def inner(func):
        async def wrapper(*args, **kwargs):
            await cp.get_status_cmd()
            if obj:
                print(f'Before: {obj}')
            await func(*args, **kwargs)
            await cp.get_status_cmd()
            if obj:
                print(f'After: {obj}')
        return wrapper
    return inner


async def set_mode_arming(cp: CP, arm: bool):
    await cmd(cp, cp.control_panel.areas[1])(cp.set_arming)(arm=arm)


async def handle_mode_command(cp: CP, mode: str):
    if mode == 'arm':
        await set_mode_arming(cp, True)
    elif mode == 'disarm':
        await set_mode_arming(cp, False)


async def handle_siren_command(cp: CP, status: bool):
    await cmd(cp, cp.control_panel.siren)(cp.set_siren)(on=status)


async def handle_out_command(cp: CP, out: int, status: bool):
    await cmd(cp, cp.control_panel.outputs[out])(cp.set_output)(
        id=out,
        on=status
    )


async def handle_keys_command(cp: CP, keys: List[str]):
    keys = [i for ele in keys for i in ele]
    await cmd(cp)(cp.send_keys)(keys=keys)


async def handle_command(cp: CP, args: Args):
    if args.cmd == Commands.SetMode:
        await handle_mode_command(cp, args.mode)
    if args.cmd == Commands.SetSiren:
        await handle_siren_command(cp, args.status)
    if args.cmd == Commands.SetOutput:
        await handle_out_command(cp, args.out, args.status)
    if args.cmd == Commands.SendKeys:
        await handle_keys_command(cp, args.keys)
