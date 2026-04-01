"""Main entry point for Vex."""
import sys
import click
import asyncio
import signal
from pathlib import Path
from pydantic import ValidationError

from vex_cli.app import start_fastapi
from vex_cli.bind import try_bind_ports
from vex_cli.proxy import start_proxy
from vex_cli.state import VexState
from vex_cli.models.pydantic import VexServerInfo
from vex_cli.locations import vex_pid_file
from vex_cli.pid_func import (
    read_pid_file,
    is_process_running,
    write_pid_file,
    delete_pid_file
)

import logging
logger = logging.getLogger(__name__)

@click.group()
def cli() -> None:
    """A simple FastAPI server CLI."""
    pass

async def main(server_info: VexServerInfo) -> int:
    pid_file: Path = vex_pid_file()
    
    if pid_file.exists(): 
        try:
            pid_file_data = read_pid_file(pid_file)

            #check if the process if running or file is stale
            if is_process_running(pid_file_data.pid):
                print("vex-cli is already running.")
                return 1
            
            delete_pid_file(pid_file)
        
        except (OSError, ValidationError):
            # Corrupted lock file
            delete_pid_file(pid_file)

    # if not we create a new one
    write_pid_file(
        str(server_info.server_address),
        server_info.proxy_port, 
        server_info.api_port,
        pid_file
    )
    
    tasks: list[asyncio.Task] = []
    shutdown_event = asyncio.Event()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)
    
    app_state = VexState(server_info)
        
    try:
        await app_state.initialize_db()

        proxy_task = asyncio.create_task(start_proxy(app_state))
        fastapi_task = asyncio.create_task(start_fastapi(app_state))
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        tasks = [proxy_task, fastapi_task, shutdown_task]
        
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # if shutdown_task has not finished it means one of the servers crashed
        if shutdown_task in pending:
            for task in done:
                await task  # This will raise the exception if there was one
        
        return 0

    except (asyncio.CancelledError, asyncio.TimeoutError):
        # Expected during shutdown - no error logging
        return 0
    except Exception as e:
        logger.exception("Fatal error occurred.")
        print(f"Unexpected error happened. Check logs in .")
        return 1
    finally:
        for task in tasks:
            if task and not task.done():
                task.cancel()

        if tasks:
            await asyncio.wait([t for t in tasks if t], timeout=3.0)

        delete_pid_file(pid_file)
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
        server_address=address,
        proxy_port=proxy_port,
        api_port=api_port
    )
    can_bind, port = try_bind_ports(server_info)

    if not can_bind:
        print(f"Port {port} is already in use!")
        sys.exit(1)

    code = asyncio.run(main(server_info))
    return code
    
if __name__ == "__main__":
    cli()