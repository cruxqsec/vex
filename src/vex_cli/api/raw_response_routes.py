from uuid import UUID
from typing import List, Annotated
from fastapi import APIRouter, Depends

from vex_cli.dependencies import get_raw_db
from vex_cli.database import RawDatabase
from vex_cli.models import RawResponse, ResponseStatus

raw_response_router = APIRouter()

# ==================== basic CRUD routes ====================

@raw_response_router.get("/raw/response/", response_model=List[RawResponse], status_code=200)
async def get_all_raw_responses(raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    return await raw_db.get_all(RawResponse)

@raw_response_router.get("/raw/response/{id}", response_model=RawResponse, status_code=200)
async def get_raw_response(id: UUID | int,
                           raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    return await raw_db.get(RawResponse, id)

@raw_response_router.post("/raw/response/", response_model=RawResponse, status_code=201)
async def create_raw_response(data: RawResponse,
                              raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    # we have to validate ourselves!
    obj = RawResponse.model_validate(data.model_dump(exclude_unset=True))
    return await raw_db.create(obj)

@raw_response_router.put("/raw/response/", response_model=ResponseStatus, status_code=202)
async def update_raw_response(data: RawResponse,
                              raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    # we have to validate ourselves!
    obj = RawResponse.model_validate(data.model_dump(exclude_unset=True))
    await raw_db.update(RawResponse, obj)
    return ResponseStatus(status="Success", msg="Object updated")

@raw_response_router.delete("/raw/response/{id}", response_model=ResponseStatus, status_code=202)
async def delete_raw_response(id: UUID | int,
                              raw_db: Annotated[RawDatabase, Depends(get_raw_db)]):
    await raw_db.delete(RawResponse, id)
    return ResponseStatus(status="Success", msg="Object deleted")