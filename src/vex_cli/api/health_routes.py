from os import getpid

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from vex_client.version import VERSION

"""
Endpoints:

    GET /          - redirect to swagger docs
    GET /health    - health check (status, pid, version)
"""

health_router = APIRouter()

@health_router.get("/")
async def swagger_docs():
    """Redirect to swagger docs for easy access."""
    return RedirectResponse(url="/docs")


@health_router.get("/health")
async def health_check():
    """Health check endpoint for clients to verify server."""
    return {"status": "healthy", "pid": getpid(), "version": VERSION}
