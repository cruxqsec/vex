import logging

import httpx

from vex_cli.models.pydantic import CountResponse, Scope, ScopeCreate

logger = logging.getLogger(__name__)


# ==================== Scope ====================


class ScopeApi:
    """Scope API methods sharing one pooled httpx client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_all_scopes(
        self, skip: int = 0, size: int = 10
    ) -> list[Scope]:
        try:
            response = await self._client.get(
                "/api/scope/",
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return []

    async def get_scope(self, id: int) -> Scope | None:
        try:
            response = await self._client.get(f"/api/scope/{id}")
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return None

    async def create_scope(self, scope: ScopeCreate) -> Scope | None:
        try:
            response = await self._client.post(
                "/api/scope/",
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return None

    async def update_scope(self, scope: Scope) -> bool:
        try:
            response = await self._client.put(
                "/api/scope/",
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return False

    async def delete_scope(self, id: int) -> bool:
        try:
            response = await self._client.delete(f"/api/scope/{id}")
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return False

    # ==================== Scope runtime ====================

    async def set_scope(self, id: int) -> bool:
        try:
            response = await self._client.post(f"/api/scope/set/{id}")
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return False

    async def unset_scope(self) -> bool:
        try:
            response = await self._client.post("/api/scope/unset/")
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return False

    async def get_active_scope(self) -> Scope | None:
        try:
            response = await self._client.get("/api/scope/active/")
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return None

    # ==================== Scope count ====================

    async def count_scopes(self) -> int:
        try:
            response = await self._client.get("/api/scope/count")
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
        except (ValueError, KeyError):
            logger.exception("Failed to parse response")
        return 0