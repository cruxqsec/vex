import asyncio
import logging
import httpx

from vex_client.process import INACTIVE_PROCESS

logger = logging.getLogger(__name__)


async def check_health_retries(retries: int, host: str, port: int) -> bool:
    """Calls the /health endpoint n times to check if vex-cli is running."""
    while retries > 0:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://{host}:{port}/health")
                if response.status_code == 200:
                    return True
        except httpx.TimeoutException:
            logger.debug("Health check timeout, retrying")
        except httpx.RequestError:
            logger.debug("Health check request error, retrying")
        retries -= 1
        if retries > 0:
            await asyncio.sleep(1)

    return False


async def check_health_pid(host: str, port: int) -> int:
    """Gets the pid from the /health endpoint. Return INACTIVE_PROCESS constant if it fails."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/health")
            if response.status_code == 200:
                json_response = response.json()
                return json_response["pid"]
            else:
                logger.warning(
                    "GET /health returned %d: %s",
                    response.status_code,
                    response.text,
                )
    except httpx.TimeoutException:
        logger.debug("Health check PID request timed out")
    except httpx.RequestError:
        logger.debug("Health check PID request failed")
    except (ValueError, KeyError):
        logger.exception("Health check response was not valid vex /health output")

    return INACTIVE_PROCESS
