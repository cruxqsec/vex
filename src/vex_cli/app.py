import asyncio
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from vex_cli.api.health_routes import health_router
from vex_cli.api.projects_routes import projects_router
from vex_cli.api.raw_routes import (
    raw_request_router,
    raw_response_router,
    raw_router,
)
from vex_cli.api.summary_routes import (
    request_summary_router,
    response_summary_router,
    summary_router,
)
from vex_cli.api.scope_routes import scope_router
from vex_cli.api.websockets import websocket_router
from vex_cli.errors import AppException
from vex_cli.state import VexState

logger = logging.getLogger(__name__)


async def start_fastapi(app_state: VexState):
    """Start Uvicorn ASGI server and inject VexState object into FastAPI state."""
    app = create_app()
    app.state.vex_state = app_state

    server_info = app_state.get_server_info()
    server_address = server_info.server_address
    api_port = server_info.api_port

    config = uvicorn.Config(
        app,
        host=server_address,
        port=api_port,
        access_log=False,
        # log_config=None
    )
    server = uvicorn.Server(config)

    try:
        logger.info(f"Starting FastAPI on {server_address}:{api_port}")
        await server.serve()
    except asyncio.CancelledError:
        logger.info("FastAPI server shutdown requested.")
    finally:
        try:
            await server.shutdown()
        except Exception as e:
            logger.error(f"Error during FastAPI cleanup: {e}")


def create_app() -> FastAPI:
    """Creates app object, registers exception handlers and adds all routes."""
    app = FastAPI(
        title="Vex API",
        # lifespan=lifespan
    )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """
        Handler for our custom AppException.
        We log only internal errors not if they occur from client sending bad data.
        """
        if exc.status_code >= 500:
            logger.error(f"{exc.__class__.__name__}: {exc.message}")

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def catch_all_handler(request: Request, exc: Exception):
        """Logs all unexpected exceptions."""
        logger.exception("Unexpected error")  # Logs full traceback
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "message": "Something went wrong"},
        )

    app.include_router(health_router)
    app.include_router(websocket_router, prefix="/ws")
    app.include_router(projects_router, prefix="/api")
    app.include_router(summary_router, prefix="/api")
    app.include_router(request_summary_router, prefix="/api")
    app.include_router(response_summary_router, prefix="/api")
    app.include_router(raw_request_router, prefix="/api")
    app.include_router(raw_response_router, prefix="/api")
    app.include_router(raw_router, prefix="/api")
    app.include_router(scope_router, prefix="/api")

    return app
