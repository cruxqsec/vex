"""Main entry point for Vex."""

import asyncio
import logging
import sys

import click

from vex_cli.app import start_fastapi
from vex_cli.bind import try_bind_ports
from vex_cli.locations import vex_log_directory
from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import lock_file_check
from vex_cli.proxy import start_proxy
from vex_cli.state import VexState

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """A simple FastAPI server CLI."""


async def main(server_info: VexServerInfo) -> int:
    try:
        async with lock_file_check(server_info):
            await _run_vex_tasks(server_info)
        print("Shutting down.")
        return 0
    except RuntimeError as e:
        logger.error("Error starting Vex CLI: %s", e)
        print(f"Error: {e}")
        return 1
    except ExceptionGroup as e:
        logger.exception("Multiple errors occurred during server startup")
        print(
            f"Multiple errors occurred ({len(e.exceptions)} exceptions). "
            f"See {vex_log_directory() / 'vex-cli.log'}"
        )
        return 1
    except BaseException:
        logger.exception("Fatal error in Vex CLI")
        print(
            f"An unexpected error occurred. See {vex_log_directory() / 'vex-cli.log'}"
        )
        return 1


async def _run_vex_tasks(server_info: VexServerInfo) -> None:
    tasks: list[asyncio.Task] = []

    app_state = VexState(server_info)

    try:
        await app_state.initialize_db_manager()

        proxy_task = asyncio.create_task(start_proxy(app_state))
        fastapi_task = asyncio.create_task(start_fastapi(app_state))

        tasks = [proxy_task, fastapi_task]

        # we wait until either server exits cleanly via signal-triggered shutdown or by crashing
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        crashed = [task for task in done if not task.cancelled()]
        exceptions: list[Exception] = []
        for task in crashed:
            exc = task.exception()
            if exc is not None and isinstance(exc, Exception):
                exceptions.append(exc)

        if exceptions:
            if len(exceptions) == 1:
                raise exceptions[0]
            else:
                raise ExceptionGroup("Multiple tasks crashed", exceptions)

    except asyncio.CancelledError:
        pass
    finally:
        if app_state.uvicorn_server is not None:
            # we force uvicorn to forcefully exit
            app_state.uvicorn_server.force_exit = True

        if app_state.mitmproxy_master is not None:
            app_state.mitmproxy_master.shutdown()

        for task in tasks:
            if task and not task.done():
                task.cancel()

        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*[t for t in tasks if t], return_exceptions=True),
                    timeout=5.0,
                )
            except TimeoutError:
                logger.warning("Tasks didn't shutdown within 5s, forcing exit")
                sys.exit(1)

        await app_state.shutdown()


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(vex_log_directory() / "vex-cli.log")],
    )


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
    _configure_logging()
    server_info = VexServerInfo(
        server_address=address, proxy_port=proxy_port, api_port=api_port
    )
    can_bind, port = try_bind_ports(server_info)

    if not can_bind:
        logger.error("Port %s is already in use!", port)
        print(f"Port {port} is already in use!")
        sys.exit(1)

    code = asyncio.run(main(server_info))
    sys.exit(code)


if __name__ == "__main__":
    cli()
