import logging
from uuid import UUID

import httpx

from vex_cli.models.pydantic import RawRequest, RawResponse

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


# ==================== RawRequest ====================


class RawApi:
    """Raw request/response API methods sharing one pooled httpx client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_all_raw_requests(
        self, skip: int = 0, size: int = 10
    ) -> list[RawRequest]:
        try:
            response = await self._client.get(
                "/api/raw/request/",
                params={"skip": skip, "size": size},
            )
            if response.status_code == 200:
                return [RawRequest.model_validate(r) for r in response.json()]
            else:
                logger.warning(
                    "GET /api/raw/request/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/raw/request/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/raw/request/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/raw/request/ failed to decode or validate response"
            )
        return []

    async def get_raw_request(self, id: UUID) -> RawRequest | None:
        try:
            response = await self._client.get(f"/api/raw/request/{id}")
            if response.status_code == 200:
                return RawRequest.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/raw/request/%s returned HTTP %d", id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/raw/request/%s failed to decode response", id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/raw/request/%s failed: %s", id, _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/raw/request/%s failed to decode or validate response", id
            )
        return None

    async def create_raw_request(self, raw_req: RawRequest) -> RawRequest | None:
        try:
            response = await self._client.post(
                "/api/raw/request/",
                json=raw_req.model_dump(mode="json"),
            )
            if response.status_code == 201:
                return RawRequest.model_validate(response.json())
            else:
                logger.warning(
                    "POST /api/raw/request/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("POST /api/raw/request/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "POST /api/raw/request/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("POST /api/raw/request/ failed to process data")
        return None

    async def update_raw_request(self, raw_req: RawRequest) -> bool:
        try:
            response = await self._client.put(
                "/api/raw/request/",
                json=raw_req.model_dump(mode="json"),
            )
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "PUT /api/raw/request/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("PUT /api/raw/request/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "PUT /api/raw/request/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("PUT /api/raw/request/ failed to process data")
        return False

    async def delete_raw_request(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/raw/request/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/raw/request/%s returned HTTP %d", id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("DELETE /api/raw/request/%s failed to decode response", id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "DELETE /api/raw/request/%s failed: %s", id, _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("DELETE /api/raw/request/%s failed to process response", id)
        return False

    # ==================== RawResponse ====================

    async def get_all_raw_responses(
        self, skip: int = 0, size: int = 10
    ) -> list[RawResponse]:
        try:
            response = await self._client.get(
                "/api/raw/response/",
                params={"skip": skip, "size": size},
            )
            if response.status_code == 200:
                return [RawResponse.model_validate(r) for r in response.json()]
            else:
                logger.warning(
                    "GET /api/raw/response/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/raw/response/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/raw/response/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/raw/response/ failed to decode or validate response"
            )
        return []

    async def get_raw_response(self, id: UUID) -> RawResponse | None:
        try:
            response = await self._client.get(f"/api/raw/response/{id}")
            if response.status_code == 200:
                return RawResponse.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/raw/response/%s returned HTTP %d", id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/raw/response/%s failed to decode response", id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/raw/response/%s failed: %s", id, _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/raw/response/%s failed to decode or validate response", id
            )
        return None

    async def create_raw_response(self, raw_res: RawResponse) -> RawResponse | None:
        try:
            response = await self._client.post(
                "/api/raw/response/",
                json=raw_res.model_dump(mode="json"),
            )
            if response.status_code == 201:
                return RawResponse.model_validate(response.json())
            else:
                logger.warning(
                    "POST /api/raw/response/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("POST /api/raw/response/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "POST /api/raw/response/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("POST /api/raw/response/ failed to process data")
        return None

    async def update_raw_response(self, raw_res: RawResponse) -> bool:
        try:
            response = await self._client.put(
                "/api/raw/response/",
                json=raw_res.model_dump(mode="json"),
            )
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "PUT /api/raw/response/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("PUT /api/raw/response/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "PUT /api/raw/response/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("PUT /api/raw/response/ failed to process data")
        return False

    async def delete_raw_response(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/raw/response/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/raw/response/%s returned HTTP %d", id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("DELETE /api/raw/response/%s failed to decode response", id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "DELETE /api/raw/response/%s failed: %s", id, _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("DELETE /api/raw/response/%s failed to process response", id)
        return False