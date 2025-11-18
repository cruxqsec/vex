import asyncio

from vex_cli.app import start_fastapi
from vex_cli.proxy import start_proxy
from vex_cli.state import VexState

import logging
logger = logging.getLogger(__name__)

async def main():
    try:
        # Initialize the state
        app_state = VexState()
        await app_state.initialize()

        # Start 2 main coroutines
        await asyncio.gather(
            start_proxy(app_state),
            start_fastapi(app_state)
        )
    except Exception as e:
        logger.error(f"Error caught in main: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
