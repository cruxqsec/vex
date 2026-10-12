from uuid import UUID, uuid4

import pytest

from vex_cli.errors import NotFoundError
from vex_cli.models.orm import ProjectORM
from vex_cli.models.pydantic import Project, ProjectCreate


async def test_get_all_projects(client, projects_db, project_orm):
    for _ in range(10):
        await projects_db.create(project_orm())

    # even without params we should get all 10
    resp = await client.get("/api/projects/")

    assert resp.status_code == 200
    result = resp.json()

    assert len(result) == 10


async def test_get_all_projects_skip_with_size(client, projects_db, project_orm):
    for _ in range(10):
        await projects_db.create(project_orm())

    resp = await client.get("/api/projects/", params={"skip": 5, "size": 5})

    assert resp.status_code == 200
    result = resp.json()

    assert len(result) == 5

@pytest.mark.parametrize("params", [{"skip": -1}, {"size": 0}, {"size": 51}])
async def test_get_all_projects_invalid_params(client, params):
    resp = await client.get("/api/projects/", params=params)

    assert resp.status_code == 422


async def test_get_project_invalid_uuid(client):
    resp = await client.get("/api/projects/not-a-uuid")
    assert resp.status_code == 422

async def test_get_project_by_id(client, projects_db, project_orm):
    created_project = await projects_db.create(project_orm())

    resp = await client.get(f"/api/projects/{created_project.id}")
    result = resp.json()

    assert resp.status_code == 200
    assert UUID(result["id"]) == created_project.id


async def test_get_project_by_id_doesnt_exist(client):
    id = uuid4()
    resp = await client.get(f"/api/projects/{id}")
    result = resp.json()
    assert resp.status_code == 404
    assert result["message"] == f"ProjectORM with id {id} not found"

async def test_create_project_missing_name(client):
    resp = await client.post("/api/projects/", json={})

    assert resp.status_code == 422

async def test_create_project(client, projects_db, projects_dir):
    new_project = ProjectCreate(name="alpha")
    resp = await client.post("/api/projects/", json=new_project.model_dump())

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "alpha"

    row = await projects_db.get(ProjectORM, UUID(body["id"]))
    assert row.name == "alpha"

    assert (projects_dir / body["id"]).is_dir()


async def test_create_project_already_exists(client, projects_dir):
    new_project = ProjectCreate(name="alpha")
    await client.post("/api/projects/", json=new_project.model_dump())
    resp = await client.post("/api/projects/", json=new_project.model_dump())

    assert resp.status_code == 409
    result = resp.json()
    assert result["error"] == "ConflictError"
    assert len(list(projects_dir.iterdir())) == 1


async def test_update_project_update_active(client, projects_db, project, state):
    original_project = project()
    await projects_db.create(original_project.to_orm())

    await state.set_active_project(original_project)

    updated_project = original_project.model_copy(update={"name": "Updated project name"})

    resp = await client.put(
        "/api/projects/", json=updated_project.model_dump(mode="json")
    )
    result = resp.json()

    assert resp.status_code == 202
    assert result["status"] == "Success"
    assert result["message"] == "Project updated!"
    assert state.get_active_project().id == updated_project.id
    assert state.get_active_project().name == updated_project.name


async def test_update_project_leaves_active_alone(client, projects_db, project, state):
    original_project = project()
    await projects_db.create(original_project.to_orm())

    # create new seperate project as active
    active_project = project()
    await state.set_active_project(active_project)

    updated_project = original_project.model_copy(update={"name": "Updated project name"})

    resp = await client.put(
        "/api/projects/", json=updated_project.model_dump(mode="json")
    )
    result = resp.json()

    assert resp.status_code == 202
    assert result["status"] == "Success"
    assert state.get_active_project().id == active_project.id
    assert state.get_active_project().name == active_project.name
    assert state.get_active_project().name != updated_project.name
    assert state.get_active_project().name != original_project.name

async def test_update_unknown_project_returns_404(client, project):
    resp = await client.put("/api/projects/", json=project().model_dump(mode="json"))

    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


async def test_delete_unknown_project_returns_404(client):
    resp = await client.delete(f"/api/projects/{uuid4()}")

    assert resp.status_code == 404


async def test_delete_non_active_project_keeps_active(
    client, state, db_manager, projects_db, project_orm, project, projects_dir
):
    saved = await projects_db.create(project_orm())
    (projects_dir / str(saved.id)).mkdir()
    active = project()
    await state.set_active_project(active)

    resp = await client.delete(f"/api/projects/{saved.id}")

    assert resp.status_code == 202
    assert state.get_active_project().id == active.id
    assert db_manager.is_project_active

async def test_delete_active_project(
    client, state, projects_db, project_orm, project, projects_dir
):
    saved = await projects_db.create(project_orm())
    folder = projects_dir / str(saved.id)
    folder.mkdir()
    await state.set_active_project(project(id=saved.id))

    resp = await client.delete(f"/api/projects/{saved.id}")

    assert resp.status_code == 202
    assert not folder.exists()
    assert state.get_active_project() is None
    with pytest.raises(NotFoundError):
        await projects_db.get(ProjectORM, saved.id)


async def test_select_project(
    client, state, db_manager, projects_db, project_orm, projects_dir
):
    saved = await projects_db.create(project_orm(name="alpha"))
    folder = projects_dir / str(saved.id)
    folder.mkdir()

    resp = await client.post(f"/api/projects/select/{saved.id}")

    assert resp.status_code == 202
    assert state.get_active_project().id == saved.id
    assert db_manager.is_project_active
    assert (folder / "main.db").exists()
    assert (folder / "raw.db").exists()


async def test_select_project_missing_folder_returns_404(
    client, projects_db, project_orm
):
    saved = await projects_db.create(project_orm())

    resp = await client.post(f"/api/projects/select/{saved.id}")

    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


async def test_select_unknown_project_returns_404(client):
    resp = await client.post(f"/api/projects/select/{uuid4()}")
    assert resp.status_code == 404


async def test_active_project_set(client, project, state):
    project_to_set = project()
    await state.set_active_project(project_to_set)

    resp = await client.get("/api/projects/active/")
    assert resp.status_code == 200

    active_project = Project(**resp.json())

    assert active_project.id == project_to_set.id
    assert active_project.name == project_to_set.name


async def test_active_project_none(client):
    resp = await client.get("/api/projects/active/")
    assert resp.status_code == 200
    assert resp.json() is None
