from uuid import UUID
import logging

import httpx

from vex_cli.models.pydantic import (
    CountResponse,
    FlowSummary,
    RequestSummary,
    ResponseSummary,
)

logger = logging.getLogger(__name__)


# ==================== RequestSummary ====================


async def get_all_request_summaries(
    host: str, port: int, skip: int = 0, size: int = 10
) -> list[RequestSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/summary/request/",
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
    return []


async def get_request_summary(id: UUID, host: str, port: int) -> RequestSummary | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/summary/request/{id}"
            )
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
    return None


async def create_request_summary(
    req_summary: RequestSummary, host: str, port: int
) -> RequestSummary | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{host}:{port}/api/summary/request/",
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
    return None


async def update_request_summary(
    req_summary: RequestSummary, host: str, port: int
) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://{host}:{port}/api/summary/request/",
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
    return False


async def delete_request_summary(id: UUID, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://{host}:{port}/api/summary/request/{id}"
            )
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
    return False


# ==================== ResponseSummary ====================


async def get_all_response_summaries(
    host: str, port: int, skip: int = 0, size: int = 10
) -> list[ResponseSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/summary/response/",
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
    return []


async def get_response_summary(
    id: UUID, host: str, port: int
) -> ResponseSummary | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/summary/response/{id}"
            )
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
    return None


async def create_response_summary(
    res_summary: ResponseSummary, host: str, port: int
) -> ResponseSummary | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{host}:{port}/api/summary/response/",
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
    return None


async def update_response_summary(
    res_summary: ResponseSummary, host: str, port: int
) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://{host}:{port}/api/summary/response/",
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
    return False


async def delete_response_summary(id: UUID, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://{host}:{port}/api/summary/response/{id}"
            )
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
    return False


# ==================== FlowSummary ====================


async def get_all_summaries(
    host: str, port: int, skip: int = 0, size: int = 10
) -> list[FlowSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/summary/",
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
    return []


async def get_summary(id: UUID, host: str, port: int) -> FlowSummary | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/summary/{id}")
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
    return None


async def delete_flow(flow_id: UUID, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://{host}:{port}/api/summary/{flow_id}"
            )
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
    return False


async def delete_all_flows(host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"http://{host}:{port}/api/summary/")
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
    return False


async def count_flows(host: str, port: int) -> int:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/summary/count")
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
    return 0
