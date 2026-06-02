import logging

import httpx

from vex_cli.models.pydantic import Project, ProjectCreate

logger = logging.getLogger(__name__)


async def get_all_projects(host: str, port: int) -> list[Project]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/projects/")
            if response.status_code == 200:
                result = [
                    Project.model_validate(project) for project in response.json()
                ]
                return result
    except httpx.TimeoutException:
        logger.exception("Timeout occurred")
        raise
    except httpx.RequestError:
        logger.exception("Request failed")
        raise
    return []


async def get_project(id: str, host: str, port: int) -> Project | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/projects/{id}")
            if response.status_code == 200:
                return Project.model_validate(response.json())
    except httpx.TimeoutException:
        logger.exception("Timeout occurred")
        raise
    except httpx.RequestError:
        logger.exception("Request failed")
        raise
    return None


async def create_project(
    new_project: ProjectCreate, host: str, port: int
) -> Project | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{host}:{port}/api/projects/",
                json=new_project.model_dump(mode="json"),
            )
            if response.status_code == 201:
                return Project.model_validate(response.json())
    except httpx.TimeoutException:
        logger.exception("Timeout occurred")
        raise
    except httpx.RequestError:
        logger.exception("Request failed")
        raise
    return None


async def update_project(updated_project: Project, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://{host}:{port}/api/projects/",
                json=updated_project.model_dump(mode="json"),
            )
            if response.status_code == 202:
                return True
    except httpx.TimeoutException:
        logger.exception("Timeout occurred")
        raise
    except httpx.RequestError:
        logger.exception("Request failed")
        raise
    return False


async def delete_project(id: str, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"http://{host}:{port}/api/projects/{id}")
            if response.status_code == 202:
                return True
    except httpx.TimeoutException:
        logger.exception("Timeout occurred")
        raise
    except httpx.RequestError:
        logger.exception("Request failed")
        raise
    return False


async def select_project(id: str, host: str, port: int) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{host}:{port}/api/projects/select/{id}"
            )
            if response.status_code == 202:
                return True
    except httpx.TimeoutException:
        logger.exception("Timeout occurred")
        raise
    except httpx.RequestError:
        logger.exception("Request failed")
        raise
    return False


async def get_active_project(host: str, port: int) -> Project | None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{host}:{port}/api/projects/active/")
            if response.status_code == 200 and response.json() is not None:
                return Project.model_validate(response.json())

    except httpx.TimeoutException:
        logger.exception("Timeout occurred")
        raise
    except httpx.RequestError:
        logger.exception("Request failed")
        raise
    return None
