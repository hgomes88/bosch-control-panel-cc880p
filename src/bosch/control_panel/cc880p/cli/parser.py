from argparse import ArgumentParser
from enum import Enum
from typing import List
from typing import Optional

from bosch.control_panel.cc880p.version import __version__ as version
from distutils.util import strtobool


class Commands(Enum):
    SetSiren = 0
    SetMode = 1
    SetOutput = 2
    SendKeys = 3


class Args:
    connect: str
    port: int
    cmd: Optional[Commands]
    keys: List[str]
    mode: str
    status: bool
    out: int


args = Args()


def get_parser():

    parser = ArgumentParser(description='Connects to the Control Panel')
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

    subparsers = parser.add_subparsers()

    get_cmds_parser(subparsers)

    return parser


def get_cmds_parser(subparsers):

    # Command Parser
    cmds_parser = subparsers.add_parser('cmd', help='Execute a command')
    cmds_parser.add_argument(
        'cmd',
        action='store_const',
        const=None
    )

    subparsers = cmds_parser.add_subparsers()

    get_cmd_send_keys_parser(subparsers)
    get_cmd_set_mode_parser(subparsers)
    get_cmd_set_siren_parser(subparsers)
    get_cmd_set_output_parser(subparsers)


def get_cmd_send_keys_parser(subparsers):
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


def get_cmd_set_mode_parser(subparsers):
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
    return get_parser().parse_args(namespace=args)
