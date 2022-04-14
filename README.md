<div id="top"></div>


<!-- PROJECT SHIELDS -->

[![Release][release-shield]][release-url]
[![Build][build-shield]][build-url]
[![MIT License][license-shield]][license-url]

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

[![LinkedIn][linkedin-shield]][linkedin-url]


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/hgomes88/bosch-control-panel-cc880p">
    <img src="images/cc880p.png" alt="CC880P" width="" height="">
  </a>

  <h3 align="center">Bosch Control Panel CC880P</h3>

  <p align="center">
    Library to interface with the old CC880P Bosch Alarm Control Panels
    <br />
    <a href="https://github.com/hgomes88/bosch-control-panel-cc880p"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/hgomes88/bosch-control-panel-cc880p">View Demo</a>
    ·
    <a href="https://github.com/hgomes88/bosch-control-panel-cc880p/issues">Report Bug</a>
    ·
    <a href="https://github.com/hgomes88/bosch-control-panel-cc880p/issues">Request Feature</a>
  </p>
</div>


<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#the-reason-behind">The Reason Behind</a></li>
        <li><a href="#interface">Interface</a></li>
        <ul>
            <li><a href="#wiring">Wiring</a></li>
            <ul>
                <li><a href="#uart-pinout-and-configuration">Uart Pinout and Configuration</a></li>
            </ul>
            <li><a href="#protocol">Protocol</a></li>
            <ul>
                <li><a href="#frames">Frames</a></li>
            </ul>
        </ul>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>


<!-- ABOUT THE PROJECT -->
## About the Project

### The Reason Behind

The reason behind the the development of this library, was the need turn the old Bosch Control Panel into a smart device without the need to replace it.

Home Assistant is the home automation I use, and I wanted to integrate also the Bosch control panel into it.

Because there wasn't any integration I could use for that purpose, I decided to implement the library myself and use it as dependency for the custom component [bosch_control_panel_cc880](https://github.com/hgomes88/homeassistant/tree/main/custom_components/bosch_control_panel_cc880) also developed by me for Home Assistant.

<p align="right">(<a href="#top">back to top</a>)</p>


### Interface

Thanks to [this][yes-thomas] webpage, it was possible to figure out that the interface with the control panel can be done through the UART accessible through the auxiliary module pins (see the [UART Pinout](#uart-pinout-and-configuration)).
As mentioned in the website, it is possible to completely replace the [direct link][direct-link-cable] cable usually needed to configure the control panel through the computer using the [A Link Plus][a-link-plus-sw] software.

<p align="right">(<a href="#top">back to top</a>)</p>


#### Wiring

To sniff and decode the packets supported by the control panel, it was followed the wiring as in the following diagram:

![a-link-plus-usb-diagram]

The information about A-Link Plus can be found [here][a-link-plus-sw].
The USB-TTL converter can be a device similar to [this][usb-ttl-dev].

To make the alarm remotely accessible, it was used a TCP/IP to UART bridge.
The current and tested solution was wired as following:

![esp8266-diagram]

The library `bosch-control-panel-cc880p` is part of this repository.
The `ESP8266` represents any device using that chip such as [ESP1][esp1-dev].
Note that it should be flashed with a software like [ESP-Link][esp-link-sw] to create a bridge between TCP/IP and UART.
Since `ESP1` operates at `3.3V` and `CC880P` control panel operates at `5V`, there's the need to use a level shifter, or something similar (see [this][level-shifter-website] site for examples).


A better solution would be wiring the system as the diagram below:

![elfin-ew10-diagram]

Using a device like [Elfin-EW10][elfin-ew10-dev] would prevent the usage of level shifter as it also operates at `5V`, as well as remove the need to flash any firmware as the device already provides everything needed.

<p align="right">(<a href="#top">back to top</a>)</p>


##### UART Pinout and Configuration

The pinout of the `CC880P` control panel is:
- `TX`: Auxiliary Module `Pin3` (***Note:*** The [website][yes-thomas] describes the `Pin7` by mistake)
- `RX`: Auxiliary Module `Pin7` (***Note:*** The [website][yes-thomas] describes the `Pin3` by mistake)
- `GND`: Auxiliary Module `Pin4`
- `VCC(5V)`: Auxiliary Module `Pin6`

The baud rate the control panel operates is `300`.

<p align="right">(<a href="#top">back to top</a>)</p>


#### Protocol

Since there was no information about the protocol used to send commands to the control panel and receive the corresponding responses, the approach was to connect the control panel using the [A Link Plus][a-link-plus-sw] and then sniff and decode the packets being transferred back and forth.
the following steps were followed:

1. Wiring (see [Wiring](#wiring) chapter)
2. Execute the A Link Plus and connect the Alarm (see A Link Plus manual [here][a-link-plus-manual])
3. Monitor and decode the packets (using a software similar to [this][device-monitoring-studio-sw] )

The result is presented in the [frames](#frames) section.

<p align="right">(<a href="#top">back to top</a>)</p>


##### Frames

Below are presented the decoded frames that are used by this library so far:

###### Send Keys Command

Command used to send keys to the control panel simulating the pressing of the keypad keys.

```
'Send Keys' Command

C0 <k1> <k2> <k3> <k4> <k5> <k6> <k7> <area> <nKeys> <crc>

Byte    Identifier  Comments
-------------------------------------------------------------------------------
1       C0          Hexadecimal representation of the 'Send Key' command
2-8     k<n>        Each byte is represents the key of the keypad. Can be sent
                        from 1 up to 7 keys in a single command
                        Note: Because it was not possible to determine the
                        checksum algorithm, the keys can only be sent one at a
                        time. Below is the list of the frames corresponding to
                        all the keys available:
                            '0': 0C 00 00 00 00 00 00 00 00 01 16
                            '1': 0C 01 00 00 00 00 00 00 00 01 16
                            '2': 0C 02 00 00 00 00 00 00 00 01 17
                            '3': 0C 03 00 00 00 00 00 00 00 01 19
                            '4': 0C 04 00 00 00 00 00 00 00 01 19
                            '5': 0C 05 00 00 00 00 00 00 00 01 1B
                            '6': 0C 06 00 00 00 00 00 00 00 01 1C
                            '7': 0C 07 00 00 00 00 00 00 00 01 1C
                            '8': 0C 08 00 00 00 00 00 00 00 01 1D
                            '9': 0C 09 00 00 00 00 00 00 00 01 1F
                            '#': 0C 1A 00 00 00 00 00 00 00 01 2F
                            '*': 0C 1B 00 00 00 00 00 00 00 01 31
9       area        If the alarm is configured to have multiple areas, then
                        this byte identifies the target area that the key(s)
                        will be sent to. Otherwise set it to '00'.
10      nKeys       Number of keys being sent in this command
11      crc         Frame checksum
                        Note: The checksum is not recognized so far, and thus
                        it should be manually set
```

###### Set Siren Command

Command used to enable/disable the siren

```
'Set Siren On ' Command
0E 05 00 00 00 00 00 00 00 00 1C

'Set Siren Off' Command
0E 06 00 00 00 00 00 00 00 00 1D

```

###### Set Arm Command

Command used to arm/disarm the alarm

```
'Arm' Command
0E 01 00 00 00 00 00 00 00 00 17

'Disarm' Command
0E 02 00 00 00 00 00 00 00 00 18

```

###### Set Output Command

Command used to set (enable/disable) outputs of the control panel.

```
'Set Output' Command

0E <on> <out> 00 00 00 00 00 00 00 <crc>

Byte    Identifier  Comments
-------------------------------------------------------------------------------
1       0E          Hexadecimal representation of special functions
2       on          Special function to be executed:
                        Set Output On: Set this byte to 03
                        Set Output Off: Set this byte to 04
3       out         This byte represents the index of the target output.
                      Supports setting the outputs 1-5, which values in this
                      byte are 0-4 respectively.
                      Here is the list of commands for each single output:

                            '1 On':   0E 03 00 00 00 00 00 00 00 00 1A
                            '1 Off':  0E 04 00 00 00 00 00 00 00 00 1A
                            '2 On':   0C 03 01 00 00 00 00 00 00 00 1A
                            '2 Off':  0C 04 01 00 00 00 00 00 00 00 1A
                            '3 On':   0C 03 02 00 00 00 00 00 00 00 1B
                            '3 Off':  0C 04 02 00 00 00 00 00 00 00 1B
                            '4 On':   0C 03 03 00 00 00 00 00 00 00 1D
                            '4 Off':  0C 04 03 00 00 00 00 00 00 00 1D
                            '5 On':   0C 03 04 00 00 00 00 00 00 00 1D
                            '5 Off':  0C 04 04 00 00 00 00 00 00 00 1D
4-10    XX          All those bytes should be settled to 00.
11      crc         Frame checksum
                        Note: The checksum is not recognized so far, and thus
                        it should be manually set
```

###### Get Status Command

Command used to request the overall status of the control panel.
After sending this command is expected the control panel to answer with the [`Get Status Response`](#get-status-response).

```
'Get Status' Command

01 00 00 00 91 30 19 0F 00 00 F1

Byte   Identifier   Comments
----------------------------
1       01          Hexadecimal representation of the 'Get Status' command.
2-10    XX          The meaning of those bytes are unknown, and thus should be
                        always sent shown above.
11      F1          Frame Checksum. Since the checksum algorithm is unknown and
                        this bytes of this command have always the same value,
                        the checksum value should always be 'F1'
```

###### Get Status Response

Response of [`Get Status Command`](#get-status-command). This frame contains all the relevant information about the status of the control panel.

```
'Get Status' Response

04 <out> <out> <zone> <zone> <en> <en> XX XX <area> <s/h> <m>

Byte   Identifier   Comments
----------------------------
1       04      :   Hexadecimal representation of the 'Get Status' response
2-3     out     :   Each bit set indicates whether an output is on.
                        Maximum number of outputs is 14.
                        Bits 1-8 of byte 3 correspond to the outputs 1-8 of the
                        control panel.
                        Bits 1-6 of byte 2 correspond to the outputs 9-14 of the
                        control panel.
                        Bits 7-8 of byte 2 are not used.
4-5     zone    :   Each bit set indicates whether a zone is triggered.
                        Maximum number of zones is 16.
                        Bits 1-8 of byte 4 correspond to the zones 1-8 of the
                        control panel.
                        Bits 1-8 of byte 5 correspond to the zones 9-16 of the
                        control panel.
6-7     en      :   Each bit set indicates whether a zone is enabled (only
                        applied when the mode of the alarm is set to `STAY`, as
                        in this mode is possible to have only a subset of zones
                        enabled).
                        Bits 1-8 of byte 6 correspond to the zones 1-8 of the
                        control panel.
                        Bits 1-8 of byte 7 correspond to the zones 9-16 of the
                        control panel.
8-9     XX      :   Unknown and not used bytes.
10      area    :   Indicates whether the stay status as well as the away
                        status of the control panel is enabled for each area.
                        Maximum number if areas is 4.
                        Bits 1-4 correspond to the away status of the areas 1-4
                        Bits 5-8 correspond to the stay status of the areas 5-8
11      s/h   :   Indicate the status of the siren (1 bit) + the current hours.
                        Bit 6 if set mean the siren is triggered.
                        Bits 0-4 represents the hours (0h-23h)
                        Other bits are not used and thus unknown.
12      m   :   Indicate the current minutes.
                        Bits 0-5 represents the minutes (0m-59m).
                        Other bits are not used and thus unknown.
```

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

This library provides a CLI (Command Line Interface) to interact with the
control panel.

### Prerequisites

### Installation

The installation of the library, including the CLI, is as simple as run:
```
$ pip install .
```

After that, the library is ready to be used, and now the CLI can be used.
To get help how to use it type in the terminal the following:

```
$ control_panel -h
```

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
## Usage

After following the [`Installation`](#installation) section, now the usage of
the CLI can be found by running:
```
$ control_panel -h
usage: control_panel [-h] [-v] -c IP -p PORT {cmd} ...

Connects to the Control Panel

positional arguments:
  {cmd}
    cmd                 Execute a command

options:
  -h, --help            show this help message and exit
  -v, --version         Gets the current version
  -c IP, --connect IP   the host ip
  -p PORT, --port PORT  the host port
```

There are 2 options to run the CLI as shown in the following sections.

### Run in Listen Mode

In this mode, the script will connect to the control panel in listening only mode, where it will output any kind of change on the control panel.

To run it the minimum should be:

```
$ control_panel -c 192.168.1.22 -p 23
```

### Run in Commanding Mode

This mode, allows the user to send commands to the control panel.
To see the list of available commands the user can do:
```
$ control_panel -c <ip> -p <port> cmd -h
usage: control_panel cmd [-h]  {sendKeys,setMode,setSiren,setOut} ...

positional arguments:
  cmd
  {sendKeys,setMode,setSiren,setOut}
    sendKeys            Sends a set of keys to the control panel. Currently supports the following: [0-9*#]{1,7}
    setMode             Change the control panel mode like arm, disarm, etc
    setSiren            Change the control panel siren status
    setOut              Change the output status of the control panel

options:
  -h, --help            show this help message and exit
```

The following are some examples:

```
$ control_panel -c <ip> -p <port> cmd setSiren off
Before: Siren(on=True)
After: Siren(on=False)
```

```
$ control_panel -c <ip> -p <port> cmd setSiren 1
Before: Siren(on=False)
After: Siren(on=True)
```

```
$ control_panel -c <ip> -p <port> cmd setSiren 1
Before: Siren(on=False)
After: Siren(on=True)
```

```
$ control_panel -c <ip> -p <port> cmd setOut 3 on
Before: Output(on=False)
After: Output(on=True)
```

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- ROADMAP -->
## Roadmap

- [ ] Complete documentation:
  - [X] Hardware Used
  - [X] Block diagram of the involved hardware
  - [X] Table of the packets (commands and responses)
  - [ ] Other
- [X] Configure precommit and linter
- [ ] Implement the battery of unit/integration tests
- [X] Implement a commandline interface
- [ ] Gracefully shutdown when a signal is received (e.g. A keyboard Interrupt)

See the [open issues](https://github.com/hgomes88/bosch-control-panel-cc880p/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- CONTRIBUTING -->
## Contributing

To contribute to this project, you need to execute the following steps:

1. Install
    1. Create a virtual environment (see how to [here][venv-website]):

    2. Activate the virtual environment (see how to [here][venv-website]):

    3. Install all the requirements for development:

        `pip install -e ".[dev]"`

    4. Install pre-commit:

        `pre-commit install`

2. Create new feature and commit the changes

    1. Create a new feature branch based from the main branch:

        `git checkout -b feature/<feature_name>`

    2. Implement the changes for the feature

    3. Run formatters/linters:

        1. Autopep8:

            `autopep8 src/ tests/`

        1. Flake8:

            `flake8 src/ tests/`

        1. Mypy:

            `mypy src/ tests/`

    4. Commit the changes (this should run pre-commit to format/lint anyway)

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- LICENSE -->
## License

Distributed under the Apache License Version 2.0. See `LICENSE.txt` for more information.

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- CONTACT -->
## Contact

Hugo Gomes - hgomes88@gmail.com

Project Link: [https://github.com/hgomes88/bosch-control-panel-cc880p](https://github.com/hgomes88/bosch-control-panel-cc880p)

Pipy Releases: [https://pypi.org/project/bosch-control-panel-cc880p](https://pypi.org/project/bosch-control-panel-cc880p)


<p align="right">(<a href="#top">back to top</a>)</p>


<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [[othneildrew] Best Readme Template](https://github.com/othneildrew/Best-README-Template/blob/master/README.md)
* [[Yes Thomas] Programming Bosh Alarm Panel without direct link cable](https://yesthomas.com/Electronics/201607%20Bosch%20Alarm%20panel%20programming%20without%20Direct%20Link%20cable.html)


<p align="right">(<a href="#top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[build-shield]: https://img.shields.io/github/workflow/status/hgomes88/bosch-control-panel-cc880p/Test/main?style=for-the-badge
[build-url]: https://github.com/hgomes88/bosch-control-panel-cc880p/actions/workflows/on-push.yml

[release-shield]:https://img.shields.io/pypi/v/bosch-control-panel-cc880p?label=Release&style=for-the-badge
[release-url]: https://pypi.org/project/bosch-control-panel-cc880p/

[contributors-shield]: https://img.shields.io/github/contributors/hgomes88/bosch-control-panel-cc880p.svg?style=for-the-badge
[contributors-url]: https://github.com/hgomes88/bosch-control-panel-cc880p/graphs/contributors

[forks-shield]: https://img.shields.io/github/forks/hgomes88/bosch-control-panel-cc880p.svg?style=for-the-badge
[forks-url]: https://github.com/hgomes88/bosch-control-panel-cc880p/network/members

[stars-shield]: https://img.shields.io/github/stars/hgomes88/bosch-control-panel-cc880p.svg?style=for-the-badge
[stars-url]: https://github.com/hgomes88/bosch-control-panel-cc880p/stargazers

[issues-shield]: https://img.shields.io/github/issues/hgomes88/bosch-control-panel-cc880p.svg?style=for-the-badge
[issues-url]: https://github.com/hgomes88/bosch-control-panel-cc880p/issues

[license-shield]: https://img.shields.io/github/license/hgomes88/bosch-control-panel-cc880p.svg?style=for-the-badge
[license-url]: https://github.com/hgomes88/bosch-control-panel-cc880p/blob/master/LICENSE.txt

[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/hugohomes

[venv-website]: https://docs.python.org/3/library/venv.html

[yes-thomas]: https://yesthomas.com/Electronics/201607%20Bosch%20Alarm%20panel%20programming%20without%20Direct%20Link%20cable.html
[a-link-plus-sw]: https://boschsecurityaustralia.freshdesk.com/support/solutions/articles/35000134094-a-link-plus-downloads-
[a-link-plus-manual]: https://resources-boschsecurity-cdn.azureedge.net/public/documents/Operation_Manual_Operation_Manual_enUS_2599016459.pdf
[direct-link-cable]: https://commerce.boschsecurity.com/sg/en/DIRECT-LINK-CABLE-SOL-16/p/4.998.800.022/
[device-monitoring-studio-sw]: https://www.hhdsoftware.com/device-monitoring-studio
[usb-ttl-dev]: https://5.imimg.com/data5/XL/VE/MY-1833510/ft232rl-usb-to-ttl-5v-3-3v-convertor.pdf
[esp1-dev]: https://en.wikipedia.org/wiki/ESP8266#/media/File:ESP-01.jpg
[esp-link-sw]: https://github.com/jeelabs/esp-link
[level-shifter-website]: https://randomnerdtutorials.com/how-to-level-shift-5v-to-3-3v/
[elfin-ew10-dev]: http://www.hi-flying.com/elfin-ew10-elfin-ew11

[product-screenshot]: images/screenshot.png
[a-link-plus-usb-diagram]: images/a-link-plus-usb-diagram.png
[elfin-ew10-diagram]: images/elfin-ew10-diagram.png
[esp8266-diagram]: images/esp8266-diagram.png
