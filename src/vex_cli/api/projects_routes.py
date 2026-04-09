import logging
import shutil
import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query

from vex_cli.database.projects_db import ProjectsDatabase
from vex_cli.dependencies import get_projects_db, get_state_object
from vex_cli.locations import vex_projects_directory
from vex_cli.models.orm import ProjectORM
from vex_cli.models.pydantic import Project, ProjectCreate, ResponseStatus
from vex_cli.state import VexState

logger = logging.getLogger(__name__)

projects_router = APIRouter()

# ==================== basic CRUD routes ====================


@projects_router.get("/projects/", response_model=List[Project], status_code=200)
async def get_all_projects(
    projects_db: Annotated[ProjectsDatabase, Depends(get_projects_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await projects_db.get_all(ProjectORM, skip, size)


@projects_router.get("/projects/{project_id}", response_model=Project, status_code=200)
async def get_project_by_id(
    project_id: uuid.UUID,
    projects_db: Annotated[ProjectsDatabase, Depends(get_projects_db)],
):
    return await projects_db.get(ProjectORM, project_id)


@projects_router.post("/projects/", response_model=Project, status_code=201)
async def create_project(
    project: ProjectCreate,
    projects_db: Annotated[ProjectsDatabase, Depends(get_projects_db)],
):
    """
    Create the project directory (under APP_DIR/projects/) and the project
    Returns the created object
    """
    project_orm = ProjectORM(**project.model_dump())
    created_project = await projects_db.create(project_orm)

    path = vex_projects_directory() / str(created_project.id)
    path.mkdir(exist_ok=True)

    return created_project


@projects_router.put("/projects/", response_model=ResponseStatus, status_code=202)
async def update_project(
    project: Project,
    projects_db: Annotated[ProjectsDatabase, Depends(get_projects_db)],
):
    """
    Update a project from a given project.
    """
    # TODO check if the project being updated is an active project
    await projects_db.update(ProjectORM, project.to_orm())

    return ResponseStatus(status="Success", msg="Object updated")


@projects_router.delete(
    "/projects/{project_id}", response_model=ResponseStatus, status_code=202
)
async def delete_project(
    project_id: uuid.UUID, state_obj: Annotated[VexState, Depends(get_state_object)]
):
    """
    Deletes the database entry and the project directory
    """
    db_manager = state_obj.get_db_manager()

    await db_manager.projects_db.delete(ProjectORM, project_id)

    path = vex_projects_directory() / str(project_id)
    if path.exists() and path.is_dir():
        shutil.rmtree(path)  # delete directory

    active_project = state_obj.get_active_project()

    if active_project is not None and active_project.id == project_id:
        await state_obj.set_active_project(None)

    return ResponseStatus(status="Success", msg="Object deleted")


# ==================== other routes ====================


@projects_router.get(
    "/projects/select/{project_id}", response_model=ResponseStatus, status_code=202
)
async def select_project(
    project_id: uuid.UUID, state_obj: Annotated[VexState, Depends(get_state_object)]
):
    """
    Selects the project as active.
    """
    db_manager = state_obj.get_db_manager()

    project_row = await db_manager.projects_db.get(ProjectORM, project_id)
    project = Project.model_validate(project_row)

    project_path = vex_projects_directory() / str(project_id)
    await db_manager.switch_project_databases(project_path)

    await state_obj.set_active_project(project)

    return ResponseStatus(
        status="Success", msg=f"Switched to project with id:{project_id}"
    )


@projects_router.get("/projects/active/", status_code=200)
async def active_project(state_obj: Annotated[VexState, Depends(get_state_object)]):
    """
    Returns the active project or None.
    """
    return state_obj.get_active_project()
