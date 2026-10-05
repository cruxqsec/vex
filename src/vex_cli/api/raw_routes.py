from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from vex_cli.database.raw_db import RawDatabase
from vex_cli.dependencies import get_raw_db
from vex_cli.models.orm import RawRequestORM, RawResponseORM
from vex_cli.models.pydantic import RawRequest, RawResponse

raw_request_router = APIRouter(tags=["Raw requests"])
raw_response_router = APIRouter(tags=["Raw responses"])

# ==================== raw request CRUD routes ====================


@raw_request_router.get(
    "/raw/request/", response_model=list[RawRequest], status_code=200
)
async def get_all_raw_requests(
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await raw_db.get_all(RawRequestORM, skip, size)


@raw_request_router.get("/raw/request/{id}", response_model=RawRequest, status_code=200)
async def get_raw_request(
    id: UUID | int, raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    return await raw_db.get(RawRequestORM, id)


# ==================== raw response CRUD routes ====================


@raw_response_router.get(
    "/raw/response/", response_model=list[RawResponse], status_code=200
)
async def get_all_raw_responses(
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await raw_db.get_all(RawResponseORM, skip, size)


@raw_response_router.get(
    "/raw/response/{id}", response_model=RawResponse, status_code=200
)
async def get_raw_response(
    id: UUID | int, raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    return await raw_db.get(RawResponseORM, id)
