import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.dependencies import get_flow_scope, get_summaries_db
from vex_cli.flow_scope import FlowScope
from vex_cli.models.orm import ScopeORM
from vex_cli.models.pydantic import CountResponse, ResponseStatus, Scope, ScopeCreate

logger = logging.getLogger(__name__)

"""
Endpoints:

    Scope CRUD endpoints:
    GET /scope/          - get all scopes
    GET /scope/count     - count scopes
    GET /scope/{id}      - get scope by id
    POST /scope/         - create scope
    PUT /scope/          - update scope
    DELETE /scope/{id}   - delete scope by id

    Scope selection endpoints:
    POST /scope/set/{id}   - set scope as active
    POST /scope/unset/     - unset the active scope
    GET /scope/active/     - get the active scope
"""


scope_router = APIRouter(tags=["Scope"])

# ==================== scope CRUD routes ====================


@scope_router.get("/scope/", response_model=list[Scope], status_code=200)
async def get_all_scopes(
    scope_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    scopes = await scope_db.get_all(ScopeORM, skip, size)
    return [Scope.from_orm(s) for s in scopes]


@scope_router.get("/scope/count", response_model=CountResponse, status_code=200)
async def count_scopes(
    scope_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    count = await scope_db.count(ScopeORM)
    return CountResponse(count=count)


@scope_router.get("/scope/{id}", response_model=Scope, status_code=200)
async def get_scope(
    id: int,
    scope_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    scope = await scope_db.get(ScopeORM, id)
    return Scope.from_orm(scope)


@scope_router.post("/scope/", response_model=Scope, status_code=201)
async def create_scope(
    scope: ScopeCreate,
    scope_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    created = await scope_db.create(scope.to_orm())
    return Scope.from_orm(created)


@scope_router.put("/scope/", response_model=ResponseStatus, status_code=202)
async def update_scope(
    scope: Scope,
    scope_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    flow_scope: Annotated[FlowScope, Depends(get_flow_scope)],
):
    await scope_db.update(ScopeORM, scope.to_orm())
    active = flow_scope.get_active_scope()
    if active and active.id == scope.id:
        flow_scope.set_active_scope(scope)
    return ResponseStatus(status="Success", message="Object updated")


@scope_router.delete("/scope/{id}", response_model=ResponseStatus, status_code=202)
async def delete_scope(
    id: int,
    scope_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    flow_scope: Annotated[FlowScope, Depends(get_flow_scope)],
):
    await scope_db.delete(ScopeORM, id)
    active = flow_scope.get_active_scope()
    if active and active.id == id:
        flow_scope.set_active_scope(None)

    return ResponseStatus(status="Success", message="Object deleted")


# ==================== scope other routes ====================


@scope_router.post("/scope/set/{id}", response_model=ResponseStatus, status_code=202)
async def set_scope(
    id: int,
    flow_scope: Annotated[FlowScope, Depends(get_flow_scope)],
    scope_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    scope = await scope_db.get(ScopeORM, id)
    flow_scope.set_active_scope(Scope.from_orm(scope))
    return ResponseStatus(status="Success", message="Scope successfuly set!")


@scope_router.post("/scope/unset/", response_model=ResponseStatus, status_code=202)
async def unset_scope(
    flow_scope: Annotated[FlowScope, Depends(get_flow_scope)],
):
    flow_scope.set_active_scope(None)
    return ResponseStatus(status="Success", message="Scope successfuly unset!")


@scope_router.get("/scope/active/", response_model=Scope | None, status_code=200)
async def get_active_scope(
    flow_scope: Annotated[FlowScope, Depends(get_flow_scope)],
):
    return flow_scope.get_active_scope()
