import logging

import httpx

from vex_client.process import INACTIVE_PROCESS

logger = logging.getLogger(__name__)


def _request_failure_reason(exc: httpx.RequestError) -> str:
    # Exception messages can include URLs (and credentials), so use safe descriptions.
    if isinstance(exc, httpx.ConnectTimeout):
        return "connection timed out"
    if isinstance(exc, httpx.TimeoutException):
        return "request timed out"
    if isinstance(exc, httpx.ConnectError):
        return "could not connect to server"
    return "HTTP request failed"


class HealthApi:
    """Health-check methods sharing one pooled httpx client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def health_check_handshake(self) -> bool:
        try:
            response = await self._client.get("/health")
            if response.status_code == 200:
                return True
            else:
                logger.warning(
                    "GET /health handshake returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /health handshake failed to decode response")
        except httpx.RequestError as exc:
            logger.warning(
                "GET /health handshake failed: %s", _request_failure_reason(exc)
            )

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
                    "GET /health PID lookup returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /health PID lookup failed to decode response")
        except httpx.RequestError as exc:
            logger.warning(
                "GET /health PID lookup failed: %s", _request_failure_reason(exc)
            )
        except (ValueError, KeyError):
            logger.exception(
                "GET /health PID lookup failed to decode or validate response"
            )

        return INACTIVE_PROCESS
