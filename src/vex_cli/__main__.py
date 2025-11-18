"""Main entry point for Vex."""
import asyncio
import click

from vex_cli.app import start_fastapi
from vex_cli.proxy import start_proxy
from vex_cli.state import VexState
from vex_cli.models import ProxyInfo

import logging
logger = logging.getLogger(__name__)

@click.group()
def cli() -> None:
    """A simple FastAPI server CLI."""
    pass

async def main(proxy_info: ProxyInfo):
    try:
        app_state = VexState(proxy_info)
        await app_state.initialize_db()

        # Start server coroutines
        await asyncio.gather(
            start_proxy(app_state),
            start_fastapi(app_state)
        )
    except Exception as e:
        logger.error(f"Error caught in main: {e}")
        print(f"Error: {e}")

@cli.command()
@click.option(
    "--address",
    default="127.0.0.1",
    help="The address to bind to",
)
@click.option(
    "--proxy-port",
    default=8080,
    type=int,
    help="The port for the mitm proxy server",
)
@click.option(
    "--api-port",
    default=9000,
    type=int,
    help="The port for the API server",
)
def start(address: str, proxy_port: int, api_port: int) -> None:
    """Start both the FastAPI and proxy servers."""
    proxy_info = ProxyInfo(address, proxy_port, api_port)
    asyncio.run(main(proxy_info))
    
if __name__ == "__main__":
    cli()