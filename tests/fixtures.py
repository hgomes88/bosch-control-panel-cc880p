"""Fixtures."""
import pytest
from bosch.control_panel.cc880p.cp import CP
from bosch.control_panel.cc880p.models.cp import CpVersion


@pytest.fixture
def writer(mocker):
    """Stream Writer fixture."""
    mocked = mocker.patch(
        'bosch.control_panel.cc880p.cp.asyncio.StreamWriter',
        autospec=True
    )

    yield mocked


@pytest.fixture
def reader(mocker):
    """Stream Reader fixture."""
    mocked = mocker.patch(
        'bosch.control_panel.cc880p.cp.asyncio.StreamReader',
        autospec=True
    )

    mocked.return_value.at_eof.return_value = False
    mocked.return_value._buffer = bytearray()

    yield mocked


@pytest.fixture
def connection(mocker, reader, writer):
    """Stream connection fixture."""
    mocked = mocker.patch(
        'bosch.control_panel.cc880p.cp.asyncio.open_connection',
        autospec=True
    )
    mocked.return_value = reader.return_value, writer.return_value

    yield mocked


@pytest.fixture
async def control_panel(connection, reader) -> CP:
    """Control panel fixture."""
    # Simulate status response
    reader.return_value.readexactly.return_value = bytes([0x04] + [0] * 12)

    cp = await CP(
        ip='127.0.0.1',
        port=8888,
        model=CpVersion.S16_V14.model(),
        installer_code='0000'
    ).start()

    yield cp

    await cp.stop()
