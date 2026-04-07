"""Main entry point for Vex."""

import asyncio
import logging
import signal
import sys

import click

from vex_cli.app import start_fastapi
from vex_cli.bind import try_bind_ports
from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import pid_file_lock
from vex_cli.proxy import start_proxy
from vex_cli.state import VexState

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """A simple FastAPI server CLI."""
    pass


async def main(server_info: VexServerInfo) -> int:
    try:
        async with pid_file_lock(server_info):
            await _run_vex_tasks(server_info)
        return 0
    except RuntimeError as e:
        print(e)
        return 1
    except Exception as e:
        print(e)
        return 1


async def _run_vex_tasks(server_info: VexServerInfo) -> None:
    tasks: list[asyncio.Task] = []
    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    app_state = VexState(server_info)

    try:
        await app_state.initialize_db_manager()

        proxy_task = asyncio.create_task(start_proxy(app_state))
        fastapi_task = asyncio.create_task(start_fastapi(app_state))
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        tasks = [proxy_task, fastapi_task, shutdown_task]

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # if shutdown_task has not finished it means one of the servers crashed
        if shutdown_task in pending:
            # gather exceptions from all completed non-shutdown tasks
            crashed = [t for t in done if t is not shutdown_task and not t.cancelled()]
            for task in crashed:
                exc = task.exception()
                if exc:
                    raise exc

    except (asyncio.CancelledError, asyncio.TimeoutError):
        # Expected during shutdown - no error logging
        pass
    except Exception:
        logger.exception("Fatal error occurred.")
        print("Unexpected error happened. Check logs in.")
        raise
    finally:
        for task in tasks:
            if task and not task.done():
                task.cancel()

        if tasks:
            await asyncio.wait([t for t in tasks if t], timeout=3.0)

        await app_state.shutdown()
        print("Shutting down. See ya later alligator!")


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
def start(address: str, proxy_port: int, api_port: int) -> int:
    """Start both the FastAPI and proxy servers."""
    server_info = VexServerInfo(
        server_address=address, proxy_port=proxy_port, api_port=api_port
    )
    can_bind, port = try_bind_ports(server_info)

    if not can_bind:
        print(f"Port {port} is already in use!")
        sys.exit(1)

    code = asyncio.run(main(server_info))
    return code


if __name__ == "__main__":
    cli()
