from uuid import UUID
from typing import List, Annotated
from fastapi import APIRouter, Depends

from vex_cli.dependencies import get_summaries_db
from vex_cli.database import SummariesDatabase
from vex_cli.models import ResponseSummary, ResponseStatus

response_summary_router = APIRouter()

# ==================== basic CRUD routes ====================

@response_summary_router.get("/summary/response/", response_model=List[ResponseSummary],
                             status_code=200)
async def get_all_response_summaries(
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]
    ):
    return await summaries_db.get_all(ResponseSummary)

@response_summary_router.get("/summary/response/{id}", response_model=ResponseSummary,
                             status_code=200)
async def get_response_summary(id: UUID | int,
                       summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    return await summaries_db.get(ResponseSummary, id)

@response_summary_router.post("/summary/response/", response_model=ResponseSummary,
                              status_code=201)
async def create_response_summary(data: ResponseSummary,
                          summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    # we have to validate ourselves!
    obj = ResponseSummary.model_validate(data.model_dump(exclude_unset=True))
    return await summaries_db.create(obj)

@response_summary_router.put("/summary/response/", response_model=ResponseStatus,
                             status_code=202)
async def update_response_summary(data: ResponseSummary,
                          summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    # we have to validate ourselves!
    obj = ResponseSummary.model_validate(data.model_dump(exclude_unset=True))
    await summaries_db.update(ResponseSummary, obj)
    return ResponseStatus(status="Success", msg="Object updated")

@response_summary_router.delete("/summary/response/{id}", response_model=ResponseStatus,
                                status_code=202)
async def delete_response_summary(id: UUID | int,
                          summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    await summaries_db.delete(ResponseSummary, id)
    return ResponseStatus(status="Success", msg="Object deleted")
