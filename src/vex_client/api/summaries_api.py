import logging
from uuid import UUID

import httpx

from vex_cli.models.pydantic import (
    CountResponse,
    FlowSummary,
    RequestSummary,
    ResponseSummary,
)

logger = logging.getLogger(__name__)


# ==================== RequestSummary ====================


class SummariesApi:
    """Summary API methods sharing one pooled httpx client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_all_request_summaries(
        self, skip: int = 0, size: int = 10
    ) -> list[RequestSummary]:
        try:
            response = await self._client.get(
                "/api/summary/request/",
                params={"skip": skip, "size": size},
            )
            if response.status_code == 200:
                return [RequestSummary.model_validate(r) for r in response.json()]
            else:
                logger.warning(
                    "GET /api/summary/request/ returned %d: %s",
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

    async def get_request_summary(self, id: UUID) -> RequestSummary | None:
        try:
            response = await self._client.get(f"/api/summary/request/{id}")
            if response.status_code == 200:
                return RequestSummary.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/summary/request/%s returned %d: %s",
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

    async def create_request_summary(self, req_summary: RequestSummary) -> RequestSummary | None:
        try:
            response = await self._client.post(
                "/api/summary/request/",
                json=req_summary.model_dump(mode="json"),
            )
            if response.status_code == 201:
                return RequestSummary.model_validate(response.json())
            else:
                logger.warning(
                    "POST /api/summary/request/ returned %d: %s",
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

    async def update_request_summary(self, req_summary: RequestSummary) -> bool:
        try:
            response = await self._client.put(
                "/api/summary/request/",
                json=req_summary.model_dump(mode="json"),
            )
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "PUT /api/summary/request/ returned %d: %s",
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

    async def delete_request_summary(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/summary/request/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/request/%s returned %d: %s",
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

    # ==================== ResponseSummary ====================

    async def get_all_response_summaries(
        self, skip: int = 0, size: int = 10
    ) -> list[ResponseSummary]:
        try:
            response = await self._client.get(
                "/api/summary/response/",
                params={"skip": skip, "size": size},
            )
            if response.status_code == 200:
                return [ResponseSummary.model_validate(r) for r in response.json()]
            else:
                logger.warning(
                    "GET /api/summary/response/ returned %d: %s",
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

    async def get_response_summary(self, id: UUID) -> ResponseSummary | None:
        try:
            response = await self._client.get(f"/api/summary/response/{id}")
            if response.status_code == 200:
                return ResponseSummary.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/summary/response/%s returned %d: %s",
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

    async def create_response_summary(
        self, res_summary: ResponseSummary
    ) -> ResponseSummary | None:
        try:
            response = await self._client.post(
                "/api/summary/response/",
                json=res_summary.model_dump(mode="json"),
            )
            if response.status_code == 201:
                return ResponseSummary.model_validate(response.json())
            else:
                logger.warning(
                    "POST /api/summary/response/ returned %d: %s",
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

    async def update_response_summary(self, res_summary: ResponseSummary) -> bool:
        try:
            response = await self._client.put(
                "/api/summary/response/",
                json=res_summary.model_dump(mode="json"),
            )
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "PUT /api/summary/response/ returned %d: %s",
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

    async def delete_response_summary(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/summary/response/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/response/%s returned %d: %s",
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

    # ==================== FlowSummary ====================

    async def get_all_summaries(
        self, skip: int = 0, size: int = 10
    ) -> list[FlowSummary]:
        try:
            response = await self._client.get(
                "/api/summary/",
                params={"skip": skip, "size": size},
            )
            if response.status_code == 200:
                return [FlowSummary.model_validate(r) for r in response.json()]
            else:
                logger.warning(
                    "GET /api/summary/ returned %d: %s",
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

    async def get_summary(self, id: UUID) -> FlowSummary | None:
        try:
            response = await self._client.get(f"/api/summary/{id}")
            if response.status_code == 200:
                return FlowSummary.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/summary/%s returned %d: %s",
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

    async def delete_flow(self, flow_id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/summary/{flow_id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/%s returned %d: %s",
                    flow_id,
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

    async def delete_all_flows(self) -> bool:
        try:
            response = await self._client.delete("/api/summary/")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/ returned %d: %s",
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

    async def count_flows(self) -> int:
        try:
            response = await self._client.get("/api/summary/count")
            if response.status_code == 200:
                return CountResponse.model_validate(response.json()).count
            else:
                logger.warning(
                    "GET /api/summary/count returned %d: %s",
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
        return 0