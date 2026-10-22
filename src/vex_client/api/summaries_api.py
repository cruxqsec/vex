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


def _request_failure_reason(exc: httpx.RequestError) -> str:
    # Exception messages can include URLs (and credentials), so use safe descriptions.
    if isinstance(exc, httpx.ConnectTimeout):
        return "connection timed out"
    if isinstance(exc, httpx.TimeoutException):
        return "request timed out"
    if isinstance(exc, httpx.ConnectError):
        return "could not connect to server"
    return "HTTP request failed"


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
                    "GET /api/summary/request/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/summary/request/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/summary/request/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/summary/request/ failed to decode or validate response"
            )
        return []

    async def get_request_summary(self, id: UUID) -> RequestSummary | None:
        try:
            response = await self._client.get(f"/api/summary/request/{id}")
            if response.status_code == 200:
                return RequestSummary.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/summary/request/%s returned HTTP %d", id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/summary/request/%s failed to decode response", id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/summary/request/%s failed: %s",
                id,
                _request_failure_reason(exc),
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/summary/request/%s failed to decode or validate response", id
            )
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
                    "POST /api/summary/request/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("POST /api/summary/request/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "POST /api/summary/request/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("POST /api/summary/request/ failed to process data")
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
                    "PUT /api/summary/request/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("PUT /api/summary/request/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "PUT /api/summary/request/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("PUT /api/summary/request/ failed to process data")
        return False

    async def delete_request_summary(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/summary/request/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/request/%s returned HTTP %d",
                    id,
                    response.status_code,
                )
        except httpx.DecodingError:
            logger.exception(
                "DELETE /api/summary/request/%s failed to decode response", id
            )
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "DELETE /api/summary/request/%s failed: %s",
                id,
                _request_failure_reason(exc),
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "DELETE /api/summary/request/%s failed to process response", id
            )
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
                    "GET /api/summary/response/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/summary/response/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/summary/response/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/summary/response/ failed to decode or validate response"
            )
        return []

    async def get_response_summary(self, id: UUID) -> ResponseSummary | None:
        try:
            response = await self._client.get(f"/api/summary/response/{id}")
            if response.status_code == 200:
                return ResponseSummary.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/summary/response/%s returned HTTP %d", id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/summary/response/%s failed to decode response", id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/summary/response/%s failed: %s",
                id,
                _request_failure_reason(exc),
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/summary/response/%s failed to decode or validate response", id
            )
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
                    "POST /api/summary/response/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("POST /api/summary/response/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "POST /api/summary/response/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("POST /api/summary/response/ failed to process data")
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
                    "PUT /api/summary/response/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("PUT /api/summary/response/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "PUT /api/summary/response/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("PUT /api/summary/response/ failed to process data")
        return False

    async def delete_response_summary(self, id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/summary/response/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/response/%s returned HTTP %d",
                    id,
                    response.status_code,
                )
        except httpx.DecodingError:
            logger.exception(
                "DELETE /api/summary/response/%s failed to decode response", id
            )
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "DELETE /api/summary/response/%s failed: %s",
                id,
                _request_failure_reason(exc),
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "DELETE /api/summary/response/%s failed to process response", id
            )
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
                logger.warning("GET /api/summary/ returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("GET /api/summary/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("GET /api/summary/ failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("GET /api/summary/ failed to decode or validate response")
        return []

    async def get_summary(self, id: UUID) -> FlowSummary | None:
        try:
            response = await self._client.get(f"/api/summary/{id}")
            if response.status_code == 200:
                return FlowSummary.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/summary/%s returned HTTP %d", id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/summary/%s failed to decode response", id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/summary/%s failed: %s", id, _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/summary/%s failed to decode or validate response", id
            )
        return None

    async def delete_flow(self, flow_id: UUID) -> bool:
        try:
            response = await self._client.delete(f"/api/summary/{flow_id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/%s returned HTTP %d", flow_id, response.status_code
                )
        except httpx.DecodingError:
            logger.exception("DELETE /api/summary/%s failed to decode response", flow_id)
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "DELETE /api/summary/%s failed: %s", flow_id, _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "DELETE /api/summary/%s failed to process response", flow_id
            )
        return False

    async def delete_all_flows(self) -> bool:
        try:
            response = await self._client.delete("/api/summary/")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/summary/ returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("DELETE /api/summary/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "DELETE /api/summary/ failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception("DELETE /api/summary/ failed to process response")
        return False

    async def count_flows(self) -> int:
        try:
            response = await self._client.get("/api/summary/count")
            if response.status_code == 200:
                return CountResponse.model_validate(response.json()).count
            else:
                logger.warning(
                    "GET /api/summary/count returned HTTP %d", response.status_code
                )
        except httpx.DecodingError:
            logger.exception("GET /api/summary/count failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning(
                "GET /api/summary/count failed: %s", _request_failure_reason(exc)
            )
            raise
        except (ValueError, KeyError):
            logger.exception(
                "GET /api/summary/count failed to decode or validate response"
            )
        return 0