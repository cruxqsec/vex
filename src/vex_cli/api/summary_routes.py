from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from vex_cli.database.raw_db import RawDatabase
from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.dependencies import get_raw_db, get_summaries_db
from vex_cli.errors import NotFoundError
from vex_cli.models.orm import (
    RawRequestORM,
    RawResponseORM,
    RequestSummaryORM,
    ResponseSummaryORM,
)
from vex_cli.models.pydantic import (
    CountResponse,
    RequestSummary,
    ResponseStatus,
    ResponseSummary,
)

"""
This is all the routes for getting ResponseSummary, RequestSummary and together
summary flows
Endpoints:

    RequestSummary endpoints:
    GET /api/summary/request/        - get all request summaries
    GET /api/summary/request/{id}    - get request summary by id
    POST /api/summary/request/       - create request summary
    PUT /api/summary/request/{id}    - update request summary by id
    DELETE /api/summary/request/{id} - delete request summary by id

    ResponseSummary endpoints:
    GET /api/summary/response/        - get all response summaries
    GET /api/summary/response/{id}    - get response summary by id
    POST /api/summary/response/       - create response summary
    PUT /api/summary/response/{id}    - update response summary by id
    DELETE /api/summary/response/{id} - delete response summary by id

    FlowSummary(joined Req+Res summary) endpoints:
    GET /api/summary/        - get all response summaries
    GET /api/summary/{id}    - get response summary by id
    POST /api/summary/       - create response summary
    PUT /api/summary/{id}    - update response summary by id
    DELETE /api/summary/{id} - delete response summary by id

"""

request_summary_router = APIRouter(tags=["Request summaries"])
response_summary_router = APIRouter(tags=["Response summaries"])
summary_router = APIRouter(tags=["Full summaries"])

# ==================== basic request CRUD routes ====================


@request_summary_router.get("/summary/request/", response_model=list[RequestSummary])
async def get_all_request_summaries(
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await summaries_db.get_all(RequestSummaryORM, skip, size)


# -------------------------------------------------------------------


@request_summary_router.get("/summary/request/{flow_id}", response_model=RequestSummary)
async def get_request_summary_by_flow_id(
    flow_id: UUID,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    return await summaries_db.get_by_flow_id(RequestSummaryORM, flow_id)


# -------------------------------------------------------------------


@request_summary_router.post(
    "/summary/request/", response_model=RequestSummary, status_code=201
)
async def create_request_summary(
    req_summary: RequestSummary,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    return await summaries_db.create(req_summary.to_orm())


# -------------------------------------------------------------------


@request_summary_router.put(
    "/summary/request/", response_model=ResponseStatus, status_code=202
)
async def update_request_summary(
    req_summary: RequestSummary,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    await summaries_db.update(RequestSummaryORM, req_summary.to_orm())
    return ResponseStatus(status="Success", msg="Object updated")


# -------------------------------------------------------------------


@request_summary_router.delete(
    "/summary/request/{id}", response_model=ResponseStatus, status_code=202
)
async def delete_request_summary(
    id: UUID | int,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    await summaries_db.delete(RequestSummaryORM, id)
    return ResponseStatus(status="Success", msg="Object deleted")


# ==================== basic response CRUD routes ====================


@response_summary_router.get(
    "/summary/response/", response_model=list[ResponseSummary], status_code=200
)
async def get_all_response_summaries(
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await summaries_db.get_all(ResponseSummaryORM, skip, size)


# -------------------------------------------------------------------


@response_summary_router.get(
    "/summary/response/{flow_id}", response_model=ResponseSummary, status_code=200
)
async def get_response_summary(
    flow_id: UUID,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    return await summaries_db.get_by_flow_id(ResponseSummaryORM, flow_id)


# -------------------------------------------------------------------


@response_summary_router.post(
    "/summary/response/", response_model=ResponseSummary, status_code=201
)
async def create_response_summary(
    res_summary: ResponseSummary,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    return await summaries_db.create(res_summary.to_orm())


# -------------------------------------------------------------------


@response_summary_router.put(
    "/summary/response/", response_model=ResponseStatus, status_code=202
)
async def update_response_summary(
    res_summary: ResponseSummary,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    await summaries_db.update(ResponseSummaryORM, res_summary.to_orm())
    return ResponseStatus(status="Success", msg="Object updated")


# -------------------------------------------------------------------


@response_summary_router.delete(
    "/summary/response/{id}", response_model=ResponseStatus, status_code=202
)
async def delete_response_summary(
    id: UUID | int,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    await summaries_db.delete(ResponseSummaryORM, id)
    return ResponseStatus(status="Success", msg="Object deleted")


# ==================== basic summaryflow CRUD routes ====================


@summary_router.get("/summary/", status_code=200)
async def get_all_summaries(
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    skip: int = Query(0, ge=0),
    size: int = Query(10, ge=1, le=50),
):
    return await summaries_db.get_full_summaries(skip, size)


# -------------------------------------------------------------------


@summary_router.get("/summary/count", response_model=CountResponse, status_code=200)
async def count_flows(
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
):
    count = await summaries_db.count(RequestSummaryORM)
    return CountResponse(count=count)


# -------------------------------------------------------------------


@summary_router.get("/summary/{id}", status_code=200)
async def get_summary(
    id: UUID, summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)]
):
    return await summaries_db.get_full_summary_by_id(id)


@summary_router.delete(
    "/summary/{flow_id}", response_model=ResponseStatus, status_code=202
)
async def delete_flow(
    flow_id: UUID,
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)],
):
    await summaries_db.delete_by_flow_id(RequestSummaryORM, flow_id)

    try:
        await raw_db.delete(RawRequestORM, flow_id)
    except NotFoundError:
        pass
    try:
        await summaries_db.delete_by_flow_id(ResponseSummaryORM, flow_id)
    except NotFoundError:
        pass
    try:
        await raw_db.delete(RawResponseORM, flow_id)
    except NotFoundError:
        pass

    return ResponseStatus(status="Success", msg=f"Flow {flow_id} deleted")


@summary_router.delete("/summary/", response_model=ResponseStatus, status_code=202)
async def delete_all_flows(
    summaries_db: Annotated[SummariesDatabase, Depends(get_summaries_db)],
    raw_db: Annotated[RawDatabase, Depends(get_raw_db)],
):
    await summaries_db.delete_all(RequestSummaryORM)
    await summaries_db.delete_all(ResponseSummaryORM)
    await raw_db.delete_all(RawRequestORM)
    await raw_db.delete_all(RawResponseORM)

    return ResponseStatus(status="Success", msg="All flows deleted!")
