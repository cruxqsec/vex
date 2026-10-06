import logging
from uuid import UUID

import httpx

from vex_cli.models.pydantic import RawRequest, RawResponse

logger = logging.getLogger(__name__)


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
                    "GET /api/raw/request/ returned %d: %s",
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return []

    async def get_raw_request(self, id: UUID) -> RawRequest | None:
        try:
            response = await self._client.get(f"/api/raw/request/{id}")
            if response.status_code == 200:
                return RawRequest.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/raw/request/%s returned %d: %s",
                    id,
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
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
                    "POST /api/raw/request/ returned %d: %s",
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
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
                    "PUT /api/raw/request/ returned %d: %s",
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return False

    async def delete_raw_request(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/raw/request/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/raw/request/%s returned %d: %s",
                    id,
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
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
                    "GET /api/raw/response/ returned %d: %s",
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return []

    async def get_raw_response(self, id: UUID) -> RawResponse | None:
        try:
            response = await self._client.get(f"/api/raw/response/{id}")
            if response.status_code == 200:
                return RawResponse.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/raw/response/%s returned %d: %s",
                    id,
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
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
                    "POST /api/raw/response/ returned %d: %s",
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
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
                    "PUT /api/raw/response/ returned %d: %s",
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return False

    async def delete_raw_response(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/raw/response/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/raw/response/%s returned %d: %s",
                    id,
                    response.status_code,
                    response.text,
                )
        except httpx.TimeoutException:
            logger.exception("Timeout occurred")
            raise
        except httpx.RequestError:
            logger.exception("Request failed")
            raise
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return False