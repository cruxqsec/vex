from uuid import UUID
from typing import List, Annotated
from fastapi import APIRouter, Depends

from vex_cli.dependencies import get_summaries_db
from vex_cli.database import SummariesDatabase
from vex_cli.models import RequestSummary, ResponseStatus


request_summary_router = APIRouter()

# ==================== basic CRUD routes ====================

@request_summary_router.get("/summary/request/", response_model=List[RequestSummary])
async def get_all_request_summaries(
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]
    ):
    return await summaries_db.get_all(RequestSummary)

@request_summary_router.get("/summary/request/{id}", response_model=RequestSummary)
async def get_request_summary(id: UUID | int,
                          summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    return await summaries_db.get(RequestSummary, id)

@request_summary_router.post("/summary/request/", response_model=RequestSummary, status_code=201)
async def create_request_summary(data: RequestSummary,
                         summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    # we have to validate ourselves!
    obj = RequestSummary.model_validate(data.model_dump(exclude_unset=True))
    return await summaries_db.create(obj)

@request_summary_router.put("/summary/request/", response_model=ResponseStatus, status_code=202)
async def update_request_summary(data: RequestSummary,
                         summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    # we have to validate ourselves!
    obj = RequestSummary.model_validate(data.model_dump(exclude_unset=True))
    await summaries_db.update(RequestSummary, obj)
    return ResponseStatus(status="Success", msg="Object updated")

@request_summary_router.delete("/summary/request/{id}", response_model=ResponseStatus,
                               status_code=202)
async def delete_request_summary(id: UUID | int, 
                        summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]):
    await summaries_db.delete(RequestSummary, id)
    return ResponseStatus(status="Success", msg="Object deleted")