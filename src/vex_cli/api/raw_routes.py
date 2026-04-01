from uuid import UUID
from typing import List, Annotated
from fastapi import APIRouter, Depends, Query

from vex_cli.dependencies import get_raw_db
from vex_cli.database import RawDatabase
from vex_cli.models import RawRequest, RawResponse, ResponseStatus

raw_request_router = APIRouter()
raw_response_router = APIRouter()
raw_router = APIRouter()

# ==================== raw request CRUD routes ====================

@raw_request_router.get("/raw/request/", response_model=List[RawRequest], status_code=200)
async def get_all_raw_requests(
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await raw_db.get_all(RawRequest, skip, size)

@raw_request_router.get("/raw/request/{id}", response_model=RawRequest, status_code=200)
async def get_raw_request(
    id: UUID | int,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    return await raw_db.get(RawRequest, id)

@raw_request_router.post("/raw/request/", response_model=RawRequest, status_code=201)
async def create_raw_request(
    data: RawRequest,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    # we have to validate ourselves!
    obj = RawRequest.model_validate(data.model_dump(exclude_unset=True))
    return await raw_db.create(obj)

@raw_request_router.put("/raw/request/", response_model=ResponseStatus, status_code=202)
async def update_raw_request(
    data: RawRequest,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    # we have to validate ourselves!
    obj = RawRequest.model_validate(data.model_dump(exclude_unset=True))
    await raw_db.update(RawRequest, obj)
    return ResponseStatus(status="Success", msg="Object updated")

@raw_request_router.delete("/raw/request/{id}", response_model=ResponseStatus, status_code=202)
async def delete_raw_request(
    id: UUID | int,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    await raw_db.delete(RawRequest, id)
    return ResponseStatus(status="Success", msg="Object deleted")

# ==================== raw response CRUD routes ====================

@raw_response_router.get("/raw/response/", response_model=List[RawResponse], status_code=200)
async def get_all_raw_responses(
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await raw_db.get_all(RawResponse, skip, size)

@raw_response_router.get("/raw/response/{id}", response_model=RawResponse, status_code=200)
async def get_raw_response(
    id: UUID | int,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    return await raw_db.get(RawResponse, id)

@raw_response_router.post("/raw/response/", response_model=RawResponse, status_code=201)
async def create_raw_response(
    data: RawResponse,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    # we have to validate ourselves!
    obj = RawResponse.model_validate(data.model_dump(exclude_unset=True))
    return await raw_db.create(obj)

@raw_response_router.put("/raw/response/", response_model=ResponseStatus, status_code=202)
async def update_raw_response(
    data: RawResponse,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    # we have to validate ourselves!
    obj = RawResponse.model_validate(data.model_dump(exclude_unset=True))
    await raw_db.update(RawResponse, obj)
    return ResponseStatus(status="Success", msg="Object updated")

@raw_response_router.delete("/raw/response/{id}", response_model=ResponseStatus, status_code=202)
async def delete_raw_response(
    id: UUID | int,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    await raw_db.delete(RawResponse, id)
    return ResponseStatus(status="Success", msg="Object deleted")

# ==================== raw CRUD routes ====================

@raw_request_router.get("/raw/", status_code=200)
async def get_all_raw(
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    pass

#-------------------------------------------------------------------

@raw_request_router.get("/raw/{id}", status_code=200)
async def get_raw_by_id(
    id: UUID | int,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    pass

#-------------------------------------------------------------------

@raw_request_router.delete("/raw/", response_model=ResponseStatus, status_code=202)
async def delete_raw(
    id: UUID | int,
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)]
):
    pass

