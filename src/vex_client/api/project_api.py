import uuid
import httpx
from typing import List

from vex_cli.models import Project

async def get_all_projects(host: str, port: int) -> List[Project]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{host}:{port}/api/projects/")
        if response.status_code == 200:
            return [Project.model_validate(project) for project in response.json()]
        return []

async def get_project(id: uuid.UUID, host: str, port: int) -> Project | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{host}:{port}/api/projects/{id}")
        if response.status_code == 200:
            return Project.model_validate(response.json())
        return None

async def create_project(project: Project, host: str, port: int) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://{host}:{port}/api/projects/",
                                     json=project.model_dump())
        if response.status_code == 201:
            return True
        return False

async def update_project(project: Project, host: str, port: int) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.put(f"http://{host}:{port}/api/projects/",
                                    json=project.model_dump())
        if response.status_code == 202:
            return True
        return False

async def delete_project(id: uuid.UUID, host: str, port: int) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"http://{host}:{port}/api/projects/{id}")
        if response.status_code == 202:
            return True
        return False

async def select_project(id: uuid.UUID, host: str, port: int) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{host}:{port}/api/projects/select/{id}")
        if response.status_code == 202:
            return True
        return False

    return True
    pass

async def get_active_project(host: str, port: int) -> Project | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{host}:{port}/api/projects/active/")
        if response.status_code == 200:
            return Project.model_validate(response.json())
        return None