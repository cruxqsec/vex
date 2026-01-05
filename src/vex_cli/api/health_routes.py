from os import getpid
from fastapi import APIRouter

from vex_client.version import VERSION

health_router = APIRouter()

@health_router.get("/health")
async def health_check():
    """Health check endpoint for clients to verify server."""
    return {
        "status": "healthy",
        "pid": getpid(),
        "version": VERSION
    }