"""Command Line Commands Management."""
from typing import Any
from typing import List

from bosch.control_panel.cc880p.cli.parser import Args
from bosch.control_panel.cc880p.cli.parser import Commands
from bosch.control_panel.cc880p.cp import CP
from bosch.control_panel.cc880p.utils import checksum


def cmd(cp: CP, obj: Any = None):
    """Fetch the control panel status after any change."""
    def inner(func):
        async def wrapper(*args, **kwargs):
            # await cp.get_status()
            if obj is not None:
                print(f'Before: {obj}')
            await func(*args, **kwargs)
            # await cp.get_status()
            if obj is not None:
                print(f'After: {obj}')
        return wrapper
    return inner


async def set_mode_arming(cp: CP, arm: bool):
    """Handle the arming mode command."""
    await cmd(cp, cp.control_panel.areas[1])(cp.set_arming)(arm=arm)


async def handle_mode_command(cp: CP, mode: str):
    """Handle the mode command."""
    if mode == 'arm':
        await set_mode_arming(cp, True)
    elif mode == 'disarm':
        await set_mode_arming(cp, False)


async def handle_siren_command(cp: CP, status: bool):
    """Handle the siren command."""
    await cmd(cp, cp.control_panel.siren)(cp.set_siren)(on=status)


async def handle_out_command(cp: CP, out: int, status: bool):
    """Handle outputs command."""
    await cmd(cp, cp.control_panel.outputs[out])(cp.set_output)(
        id=out,
        on=status
    )


async def handle_keys_command(cp: CP, keys: List[str]):
    """Handle the keys sending."""
    keys = [i for ele in keys for i in ele]
    await cmd(cp)(cp.send_keys)(keys=keys)
    await cmd(cp, cp.control_panel.areas)(cp.get_status)()


async def handle_raw_command(cp: CP, raw: bytes):
    """Handle raw commands."""
    # Add the checksum calculated to the data
    _raw = raw + bytes([checksum(raw)])
    print(f'Sending: {_raw.hex()}')
    # Send the command and wait for the response
    resp = await (cp.send_command)(message=_raw)

    # Split the response checksum from its data
    resp_checksum = resp[-1]
    resp_data = resp[0:-1]
    # Calculate the checksum
    calc_checksum = checksum(resp_data)

    if calc_checksum == resp_checksum:
        print(
            f'[VALID CHECKSUM] received: {hex(resp_checksum)} | calculated: '
            f'{hex(calc_checksum)}'
        )
    else:
        print(
            f'[INVALID CHECKSUM] received: {hex(resp_checksum)} | calculated: '
            f'{hex(calc_checksum)}'
        )

    print(resp.hex())


async def handle_command(cp: CP, args: Args):
    """Handle the control panel commands."""
    if args.cmd == Commands.SetMode:
        await handle_mode_command(cp, args.mode)
    if args.cmd == Commands.SetSiren:
        await handle_siren_command(cp, args.status)
    if args.cmd == Commands.SetOutput:
        await handle_out_command(cp, args.out, args.status)
    if args.cmd == Commands.SendKeys:
        await handle_keys_command(cp, args.keys)
    if args.cmd == Commands.SendRaw:
        await handle_raw_command(cp, args.raw)
