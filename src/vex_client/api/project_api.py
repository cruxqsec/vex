import logging

import httpx

from vex_cli.models.pydantic import Project, ProjectCreate

logger = logging.getLogger(__name__)


class ProjectsApi:
    """Project API methods sharing one pooled httpx client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_all_projects(self, skip: int = 0, size: int = 50) -> list[Project]:
        try:
            response = await self._client.get(
                "/api/projects/",
                params={"skip": skip, "size": size},
            )
            if response.status_code == 200:
                result = [
                    Project.model_validate(project) for project in response.json()
                ]
                return result
            else:
                logger.warning(
                    "GET /api/projects/ returned %d: %s",
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

    async def get_project(self, id: str) -> Project | None:
        try:
            response = await self._client.get(f"/api/projects/{id}")
            if response.status_code == 200:
                return Project.model_validate(response.json())
            else:
                logger.warning(
                    "GET /api/projects/%s returned %d: %s",
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

    async def create_project(self, new_project: ProjectCreate) -> Project | None:
        try:
            response = await self._client.post(
                "/api/projects/",
                json=new_project.model_dump(mode="json"),
            )
            if response.status_code == 201:
                return Project.model_validate(response.json())
            else:
                logger.warning(
                    "POST /api/projects/ returned %d: %s",
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

    async def update_project(self, updated_project: Project) -> bool:
        try:
            response = await self._client.put(
                "/api/projects/",
                json=updated_project.model_dump(mode="json"),
            )
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "PUT /api/projects/ returned %d: %s",
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

    async def delete_project(self, id: str) -> bool:
        try:
            response = await self._client.delete(f"/api/projects/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "DELETE /api/projects/%s returned %d: %s",
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

    async def select_project(self, id: str) -> bool:
        try:
            response = await self._client.post(f"/api/projects/select/{id}")
            if response.status_code == 202:
                return True
            else:
                logger.warning(
                    "POST /api/projects/select/%s returned %d: %s",
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

    async def get_active_project(self) -> Project | None:
        try:
            response = await self._client.get("/api/projects/active/")
            if response.status_code == 200 and response.json() is not None:
                return Project.model_validate(response.json())
            elif response.status_code != 204:
                logger.warning(
                    "GET /api/projects/active/ returned %d: %s",
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