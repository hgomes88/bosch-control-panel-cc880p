"""Control panel command line parser."""
from argparse import ArgumentParser
from enum import Enum
from typing import List
from typing import Optional

from bosch.control_panel.cc880p.version import __version__ as version
from distutils.util import strtobool


class Commands(Enum):
    """Supported Commands."""

    SetSiren = 0
    SetMode = 1
    SetOutput = 2
    SendKeys = 3
    SendRaw = 4


class Args:
    """Parser arguments."""

    connect: str
    port: int
    cmd: Optional[Commands]
    keys: List[str]
    mode: str
    status: bool
    out: int


args = Args()


def get_parser():
    """Get the argument parser."""
    parser = ArgumentParser(description='Connects to the Control Panel')
    parser.add_argument(
        'cmd',
        action='store_const',
        const=None
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=version,
        help='Gets the current version'
    )
    parser.add_argument(
        '-c', '--connect',
        required=True,
        metavar='IP',
        type=str,
        help='the host ip'
    )
    parser.add_argument(
        '-p', '--port',
        required=True,
        metavar='PORT',
        type=int,
        help='the host port'
    )

    parser.add_argument(
        '-i', '--code',
        required=False,
        metavar='INSTALLER_CODE',
        type=str,
        help='the installer code'
    )

    subparsers = parser.add_subparsers()

    get_cmds_parser(subparsers)

    return parser


def get_cmds_parser(subparsers):
    """Get commands parser."""
    # Command Parser
    cmds_parser = subparsers.add_parser('cmd', help='Execute a command')

    subparsers = cmds_parser.add_subparsers()

    get_cmd_send_keys_parser(subparsers)
    get_cmd_send_raw_parser(subparsers)
    get_cmd_set_mode_parser(subparsers)
    get_cmd_set_siren_parser(subparsers)
    get_cmd_set_output_parser(subparsers)


def get_cmd_send_keys_parser(subparsers):
    """Send keys command parser."""
    # SEND KEYS command
    cmd_send_keys_parser = subparsers.add_parser(
        'sendKeys',
        help='Sends a set of keys to the control panel. Currently supports the'
        ' following: [0-9*#]{1,7}'
    )
    cmd_send_keys_parser.add_argument(
        'cmd',
        action='store_const',
        const=Commands.SendKeys
    )
    cmd_send_keys_parser.add_argument(
        'keys',
        nargs='+',
        type=str,
        help='The keys to execute'
    )


def get_cmd_send_raw_parser(subparsers):
    """Send raw command parser."""
    # SEND Raw command
    cmd_send_raw_parser = subparsers.add_parser(
        'sendRaw',
        help='Sends a set of bytes to the control panel.'
    )
    cmd_send_raw_parser.add_argument(
        'cmd',
        action='store_const',
        const=Commands.SendRaw
    )

    def string_to_bytes(string: str) -> bytes:
        return bytes.fromhex(string)

    cmd_send_raw_parser.add_argument(
        'raw',
        type=lambda string: bytes.fromhex(string),
        help='The byte to send'
    )


def get_cmd_set_mode_parser(subparsers):
    """Set mode command parser."""
    # SET MODE command
    cmd_set_mode_parser = subparsers.add_parser(
        'setMode',
        help='Change the control panel mode like arm, disarm, etc'
    )
    cmd_set_mode_parser.add_argument(
        'cmd',
        action='store_const',
        const=Commands.SetMode
    )
    cmd_set_mode_parser.add_argument(
        'mode',
        choices=['arm', 'disarm'],
        help='Changes the control panel mode'
    )


def get_cmd_set_siren_parser(subparsers):
    """Set siren command parser."""
    cmd_set_siren_parser = subparsers.add_parser(
        'setSiren',
        help='Change the control panel siren status'
    )
    cmd_set_siren_parser.add_argument(
        'cmd',
        action='store_const',
        const=Commands.SetSiren
    )
    cmd_set_siren_parser.add_argument(
        'status',
        type=lambda x: bool(strtobool(x)),
        help='Changes the status of the siren'
    )


def get_cmd_set_output_parser(subparsers):
    """Set output parser."""
    # SET OUTPUT command
    cmd_set_out_parser = subparsers.add_parser(
        'setOut',
        help='Change the output status of the control panel'
    )
    cmd_set_out_parser.add_argument(
        'cmd',
        action='store_const',
        const=Commands.SetOutput
    )
    cmd_set_out_parser.add_argument(
        'out',
        type=int,
        help='Changes the output'
    )
    cmd_set_out_parser.add_argument(
        'status',
        type=lambda x: bool(strtobool(x)),
        help='Changes the output'
    )


def get_args():
    """Parse and get the arguments."""
    return get_parser().parse_args(namespace=args)
