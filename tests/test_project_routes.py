import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from vex_cli.app import create_app
from vex_cli.dependencies import get_projects_db, get_state_object
from vex_cli.models.orm import ProjectORM
from vex_cli.models.pydantic import Project, ProjectCreate
from vex_cli.errors import NotFoundError


def make_project_orm(id: UUID | None = None, name: str = "Test Project"):
    project = ProjectORM()
    project.id = uuid4() if id is None else id
    project.name = name
    project.created_at = datetime.now()
    project.updated_at = datetime.now()
    return project


def make_project(id: UUID | None = None, name: str = "Test Project"):
    project_id = uuid4() if id is None else id
    return Project(
        id=project_id,
        name=name,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def make_project_create(name: str = "Test Project"):
    return ProjectCreate(name=name)


@pytest_asyncio.fixture
async def mock_projects_db():
    return AsyncMock()


@pytest_asyncio.fixture
async def mock_state_obj():
    state = MagicMock()
    state.get_db_manager.return_value.projects_db = AsyncMock()
    state.get_db_manager.return_value.close_project_databases = AsyncMock()
    return state


@pytest_asyncio.fixture
async def client(mock_projects_db, mock_state_obj):
    app = create_app()
    app.dependency_overrides[get_projects_db] = lambda: mock_projects_db
    app.dependency_overrides[get_state_object] = lambda: mock_state_obj
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# --- GET /projects/ ---


@pytest.mark.asyncio
async def test_get_all_projects_returns_200(client, mock_projects_db):
    mock_projects_db.get_all.return_value = [make_project()]

    response = await client.get("/api/projects/")

    assert response.status_code == 200
    mock_projects_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_projects_returns_empty_list(client, mock_projects_db):
    mock_projects_db.get_all.return_value = []

    response = await client.get("/api/projects/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_projects_with_pagination(client, mock_projects_db):
    mock_projects_db.get_all.return_value = [make_project()]

    response = await client.get("/api/projects/?skip=10&size=20")

    assert response.status_code == 200
    mock_projects_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_projects_rejects_invalid_size(client, mock_projects_db):
    response = await client.get("/api/projects/?size=999")

    assert response.status_code == 422


# --- GET /projects/{project_id} ---


@pytest.mark.asyncio
async def test_get_project_by_id_returns_200(client, mock_projects_db):
    project_id = uuid4()
    mock_projects_db.get.return_value = make_project(id=project_id)

    response = await client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    mock_projects_db.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_project_by_id_not_found(client, mock_projects_db):
    project_id = uuid4()
    mock_projects_db.get.side_effect = NotFoundError("Project not found")

    response = await client.get(f"/api/projects/{project_id}")

    assert response.status_code == 404


# --- POST /projects/ ---


@pytest.mark.asyncio
async def test_create_project_returns_201(client, mock_projects_db, mocker):
    project_id = uuid4()
    created_project = make_project(id=project_id, name="New Project")
    mock_projects_db.create.return_value = created_project

    # Mock the directory creation
    mocker.patch("vex_cli.api.projects_routes.vex_projects_directory")
    mocker.patch("pathlib.Path.mkdir")

    payload = {"name": "New Project"}

    response = await client.post("/api/projects/", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "New Project"
    mock_projects_db.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_project_invalid_payload(client, mock_projects_db):
    response = await client.post("/api/projects/", json={"bad": "data"})

    assert response.status_code == 422


# --- PUT /projects/ ---


@pytest.mark.asyncio
async def test_update_project_returns_202(client, mock_projects_db):
    project_id = uuid4()
    project = make_project(id=project_id, name="Updated Project")
    mock_projects_db.update.return_value = None

    response = await client.put(
        "/api/projects/",
        json={
            "id": str(project_id),
            "name": "Updated Project",
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_update_project_not_found(client, mock_projects_db):
    project_id = uuid4()
    mock_projects_db.update.side_effect = NotFoundError("Not found")

    response = await client.put(
        "/api/projects/",
        json={
            "id": str(project_id),
            "name": "Updated Project",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
    )

    assert response.status_code == 404


# --- DELETE /projects/{project_id} ---


@pytest.mark.asyncio
async def test_delete_project_returns_202(client, mock_state_obj, mocker):
    project_id = uuid4()
    mock_state_obj.get_db_manager().projects_db.delete.return_value = None
    mock_state_obj.get_active_project.return_value = None

    # Mock the directory deletion
    mocker.patch("vex_cli.api.projects_routes.vex_projects_directory")
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.is_dir", return_value=True)
    mocker.patch("shutil.rmtree")

    response = await client.delete(f"/api/projects/{project_id}")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_delete_project_not_found(client, mock_state_obj):
    project_id = uuid4()
    mock_state_obj.get_db_manager().projects_db.delete.side_effect = NotFoundError(
        "Not found"
    )

    response = await client.delete(f"/api/projects/{project_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_also_unsets_active_project(
    client, mock_state_obj, mocker
):
    project_id = uuid4()
    active_project = make_project(id=project_id)
    mock_state_obj.get_db_manager().projects_db.delete.return_value = None
    mock_state_obj.get_active_project.return_value = active_project
    mock_state_obj.set_active_project = AsyncMock()

    mocker.patch("vex_cli.api.projects_routes.vex_projects_directory")
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.is_dir", return_value=True)
    mocker.patch("shutil.rmtree")

    response = await client.delete(f"/api/projects/{project_id}")

    assert response.status_code == 202
    mock_state_obj.set_active_project.assert_called_once_with(None)
    mock_state_obj.get_flow_scope().set_active_scope.assert_called_once_with(None)
    mock_state_obj.get_db_manager().close_project_databases.assert_called_once()


# --- POST /projects/select/{project_id} ---


@pytest.mark.asyncio
async def test_select_project_returns_202(client, mock_state_obj, mocker):
    project_id = uuid4()
    project = make_project_orm(project_id, name="Selectable Project")
    mock_state_obj.get_db_manager().projects_db.get = AsyncMock(return_value=project)
    mock_state_obj.get_db_manager().switch_project_databases = AsyncMock()
    mock_state_obj.set_active_project = AsyncMock()
    mocker.patch("pathlib.Path.is_dir", return_value=True)

    response = await client.post(f"/api/projects/select/{project_id}")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"
    mock_state_obj.set_active_project.assert_called_once()


@pytest.mark.asyncio
async def test_select_project_missing_directory_returns_404(
    client, mock_state_obj, mocker, tmp_path
):
    project_id = uuid4()
    project = make_project_orm(project_id, name="Ghost Project")
    mock_state_obj.get_db_manager().projects_db.get = AsyncMock(return_value=project)
    mock_state_obj.get_db_manager().switch_project_databases = AsyncMock()
    mock_state_obj.set_active_project = AsyncMock()
    mocker.patch(
        "vex_cli.api.projects_routes.vex_projects_directory", return_value=tmp_path
    )

    response = await client.post(f"/api/projects/select/{project_id}")

    assert response.status_code == 404
    mock_state_obj.get_db_manager().switch_project_databases.assert_not_called()
    mock_state_obj.set_active_project.assert_not_called()


@pytest.mark.asyncio
async def test_select_project_not_found(client, mock_state_obj):
    project_id = uuid4()
    mock_state_obj.get_db_manager().projects_db.get.side_effect = NotFoundError(
        "Not found"
    )

    response = await client.post(f"/api/projects/select/{project_id}")

    assert response.status_code == 404
