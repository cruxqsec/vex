import logging
from uuid import UUID

import httpx

from vex_cli.models.pydantic import RawRequest, RawResponse

logger = logging.getLogger(__name__)


# ==================== RawRequest ====================


async def get_all_raw_requests(
    host: str, port: int, skip: int = 0, size: int = 10
) -> list[RawRequest]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/raw/request/",
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


async def get_raw_request(id: UUID, host: str, port: int) -> RawRequest | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/raw/request/{id}")
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


async def create_raw_request(
    raw_req: RawRequest, host: str, port: int
) -> RawRequest | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{host}:{port}/api/raw/request/",
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


async def update_raw_request(raw_req: RawRequest, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://{host}:{port}/api/raw/request/",
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


async def delete_raw_request(id: UUID, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"http://{host}:{port}/api/raw/request/{id}")
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
    host: str, port: int, skip: int = 0, size: int = 10
) -> list[RawResponse]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/raw/response/",
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


async def get_raw_response(id: UUID, host: str, port: int) -> RawResponse | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/raw/response/{id}")
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


async def create_raw_response(
    raw_res: RawResponse, host: str, port: int
) -> RawResponse | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{host}:{port}/api/raw/response/",
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


async def update_raw_response(raw_res: RawResponse, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://{host}:{port}/api/raw/response/",
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


async def delete_raw_response(id: UUID, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://{host}:{port}/api/raw/response/{id}"
            )
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
