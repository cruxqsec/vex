import asyncio
import logging

import httpx

from vex_client.process import INACTIVE_PROCESS

logger = logging.getLogger(__name__)


class HealthApi:
    """Health-check methods sharing one pooled httpx client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def check_health_retries(self, retries: int) -> bool:
        """Calls the /health endpoint n times to check if vex-cli is running."""
        while retries > 0:
            try:
                response = await self._client.get("/health")
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

    async def check_health_pid(self) -> int:
        """Gets the pid from the /health endpoint. Return INACTIVE_PROCESS constant if it fails."""
        try:
            response = await self._client.get("/health")
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