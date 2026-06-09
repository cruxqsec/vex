import logging

import httpx

from vex_cli.models.pydantic import CountResponse, Scope, ScopeCreate

logger = logging.getLogger(__name__)


# ==================== Scope ====================


async def get_all_scopes(
    host: str, port: int, skip: int = 0, size: int = 10
) -> list[Scope]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/scope/",
                params={"skip": skip, "size": size},
            )
            if response.status_code == 200:
                return [Scope.model_validate(r) for r in response.json()]
            else:
                logger.warning(
                    "GET /api/scope/ returned %d: %s",
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


async def get_scope(id: int, host: str, port: int) -> Scope | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/scope/{id}")
            if response.status_code == 200:
                return Scope.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/scope/%d returned %d: %s",
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


async def create_scope(scope: ScopeCreate, host: str, port: int) -> Scope | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{host}:{port}/api/scope/",
                json=scope.model_dump(mode="json"),
            )
            if response.status_code == 201:
                return Scope.model_validate(response.json())
            else:
                logger.warning(
                    "POST /api/scope/ returned %d: %s",
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


async def update_scope(scope: Scope, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://{host}:{port}/api/scope/",
                json=scope.model_dump(mode="json"),
            )
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "PUT /api/scope/ returned %d: %s",
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


async def delete_scope(id: int, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"http://{host}:{port}/api/scope/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/scope/%d returned %d: %s",
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


# ==================== Scope runtime ====================


async def set_scope(id: int, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://{host}:{port}/api/scope/set/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "POST /api/scope/set/%d returned %d: %s",
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


async def unset_scope(host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"http://{host}:{port}/api/scope/unset/")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "POST /api/scope/unset/ returned %d: %s",
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


async def get_active_scope(host: str, port: int) -> Scope | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/scope/active/")
            if response.status_code == 200:
                data = response.json()
                if data is None:
                    return None
                return Scope.model_validate(data)
            else:
                logger.warning(
                    "GET /api/scope/active/ returned %d: %s",
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


# ==================== Scope count ====================


async def count_scopes(host: str, port: int) -> int:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/scope/count")
            if response.status_code == 200:
                return CountResponse.model_validate(response.json()).count
            else:
                logger.warning(
                    "GET /api/scope/count returned %d: %s",
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
