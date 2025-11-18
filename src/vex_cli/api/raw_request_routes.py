from uuid import UUID
from typing import List, Annotated
from fastapi import APIRouter, Depends

from vex_cli.dependencies import get_raw_db
from vex_cli.database import RawDatabase
from vex_cli.models import RawRequest, ResponseStatus

raw_request_router = APIRouter()

# ==================== basic CRUD routes ====================

@raw_request_router.get("/raw/request/", response_model=List[RawRequest], status_code=200)
async def get_all_raw_requests(raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    return await raw_db.get_all(RawRequest)

@raw_request_router.get("/raw/request/{id}", response_model=RawRequest, status_code=200)
async def get_raw_request(id: UUID | int,
                          raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    return await raw_db.get(RawRequest, id)

@raw_request_router.post("/raw/request/", response_model=RawRequest, status_code=201)
async def create_raw_request(data: RawRequest,
                             raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    # we have to validate ourselves!
    obj = RawRequest.model_validate(data.model_dump(exclude_unset=True))
    return await raw_db.create(obj)

@raw_request_router.put("/raw/request/", response_model=ResponseStatus, status_code=202)
async def update_raw_request(data: RawRequest,
                             raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    # we have to validate ourselves!
    obj = RawRequest.model_validate(data.model_dump(exclude_unset=True))
    await raw_db.update(RawRequest, obj)
    return ResponseStatus(status="Success", msg="Object updated")

@raw_request_router.delete("/raw/request/{id}", response_model=ResponseStatus, status_code=202)
async def delete_raw_request(id: UUID | int,
                             raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    await raw_db.delete(RawRequest, id)
    return ResponseStatus(status="Success", msg="Object deleted")