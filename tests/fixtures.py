import pytest
from bosch.control_panel.cc880p.cp import CP


@pytest.fixture
async def control_panel() -> CP:
    yield CP('127.0.0.1', 8888)
