
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

from control_pannel.control_panel import ControlPanel

_LOGGER = logging.getLogger(__name__)

async def main(loop):

    _LOGGER.error("Starting example...")
    
    cp = ControlPanel("192.168.1.22", 23, loop)

    await cp.start()

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main(loop))