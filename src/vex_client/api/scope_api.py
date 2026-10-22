import logging

import httpx

from vex_cli.models.pydantic import CountResponse, Scope, ScopeCreate

logger = logging.getLogger(__name__)


def _request_failure_reason(exc: httpx.RequestError) -> str:
    # Exception messages may contain URLs or other request data.
    if isinstance(exc, httpx.ConnectTimeout):
        return "connection timed out"
    if isinstance(exc, httpx.TimeoutException):
        return "request timed out"
    if isinstance(exc, httpx.ConnectError):
        return "connection failed"
    return "request failed"


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
                logger.warning("GET /api/scope/ returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("GET /api/scope/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("GET /api/scope/ failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("GET /api/scope/ failed to decode or validate response")
        return []

    async def get_scope(self, id: int) -> Scope | None:
        try:
            response = await self._client.get(f"/api/scope/{id}")
            if response.status_code == 200:
                return Scope.model_validate(response.json())
            else:
                logger.warning("GET /api/scope/{id} returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("GET /api/scope/{id} failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("GET /api/scope/{id} failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("GET /api/scope/{id} failed to decode or validate response")
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
                logger.warning("POST /api/scope/ returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("POST /api/scope/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("POST /api/scope/ failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("POST /api/scope/ failed to decode or validate response")
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
                logger.warning("PUT /api/scope/ returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("PUT /api/scope/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("PUT /api/scope/ failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("PUT /api/scope/ failed to decode or validate response")
        return False

    async def delete_scope(self, id: int) -> bool:
        try:
            response = await self._client.delete(f"/api/scope/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning("DELETE /api/scope/{id} returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("DELETE /api/scope/{id} failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("DELETE /api/scope/{id} failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("DELETE /api/scope/{id} failed to decode or validate response")
        return False

    # ==================== Scope runtime ====================

    async def set_scope(self, id: int) -> bool:
        try:
            response = await self._client.post(f"/api/scope/set/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning("POST /api/scope/set/{id} returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("POST /api/scope/set/{id} failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("POST /api/scope/set/{id} failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("POST /api/scope/set/{id} failed to decode or validate response")
        return False

    async def unset_scope(self) -> bool:
        try:
            response = await self._client.post("/api/scope/unset/")
            if response.status_code == 202:
                return True
            else:
                logger.warning("POST /api/scope/unset/ returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("POST /api/scope/unset/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("POST /api/scope/unset/ failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("POST /api/scope/unset/ failed to decode or validate response")
        return False

    async def get_active_scope(self) -> Scope | None:
        try:
            response = await self._client.get("/api/scope/active/")
            if response.status_code == 200:
                data = response.json()
                if data is None:
                    return None
                return Scope.model_validate(data)
            elif not response.is_success:
                logger.warning("GET /api/scope/active/ returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("GET /api/scope/active/ failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("GET /api/scope/active/ failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("GET /api/scope/active/ failed to decode or validate response")
        return None

    # ==================== Scope count ====================

    async def count_scopes(self) -> int:
        try:
            response = await self._client.get("/api/scope/count")
            if response.status_code == 200:
                return CountResponse.model_validate(response.json()).count
            else:
                logger.warning("GET /api/scope/count returned HTTP %d", response.status_code)
        except httpx.DecodingError:
            logger.exception("GET /api/scope/count failed to decode response")
            raise
        except httpx.RequestError as exc:
            logger.warning("GET /api/scope/count failed: %s", _request_failure_reason(exc))
            raise
        except (ValueError, KeyError):
            logger.exception("GET /api/scope/count failed to decode or validate response")
        return 0