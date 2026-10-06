from pathlib import Path
from uuid import UUID

from sqlalchemy import RowMapping, delete, select

from vex_cli.database.base_db import BaseDatabase, T
from vex_cli.errors import NotFoundError
from vex_cli.models.orm import RequestSummaryORM, ResponseSummaryORM, ScopeORM
from vex_cli.models.pydantic import FlowSummary


class SummariesDatabase(BaseDatabase):
    _orm_models = [RequestSummaryORM, ResponseSummaryORM, ScopeORM]
    _wal_mode = True

    def __init__(self, db_path: Path):
        super().__init__(db_path)
        _exclude = {"id", "flow_id", "timestamp"}
        # RequestSummary columns to select
        self._req_cols = [
            getattr(RequestSummaryORM, c.name)
            for c in RequestSummaryORM.__table__.columns
        ]
        # ResponseSummary columns to select
        self._res_cols = [
            getattr(ResponseSummaryORM, c.name)
            for c in ResponseSummaryORM.__table__.columns
            if c.name not in _exclude
        ]

    async def get_by_flow_id(self, model: type[T], flow_id: UUID) -> T:
        async with self.session(commit=False) as s:
            result = await s.execute(
                select(model).where(model.flow_id == flow_id)  # type: ignore
            )
            obj = result.scalars().first()
            if obj is None:
                raise NotFoundError(
                    f"{model.__name__} for flow {flow_id} not found"
                )
            return obj

    async def delete_by_flow_id(self, model: type[T], flow_id: UUID) -> None:
        async with self.session() as s:
            result = await s.execute(delete(model).where(model.flow_id == flow_id))  # type: ignore
            if result.rowcount == 0:
                raise NotFoundError(
                    f"{model.__name__} for flow {flow_id} not found"
                )

    async def get_full_summaries(self, skip: int, size: int) -> list[FlowSummary]:
        """List of full summaries (Request/ResponseSummary)"""
        async with self.session(commit=False) as s:
            statement = (
                select(*self._req_cols, *self._res_cols)
                .outerjoin(
                    ResponseSummaryORM,
                    RequestSummaryORM.flow_id == ResponseSummaryORM.flow_id,
                )
                .order_by(RequestSummaryORM.timestamp, RequestSummaryORM.id)
                .offset(skip)
                .limit(size)
            )
            result = await s.execute(statement)
            return [
                FlowSummary.model_validate(dict(row)) for row in result.mappings().all()
            ]

    async def get_full_summary_by_id(self, flow_id: UUID) -> FlowSummary:
        """Get a single summary (Request/ResponseSummary). TODO: Improve return type!"""
        async with self.session(commit=False) as s:
            statement = (
                select(*self._req_cols, *self._res_cols)
                .outerjoin(
                    ResponseSummaryORM,
                    RequestSummaryORM.flow_id == ResponseSummaryORM.flow_id,
                )
                .where(RequestSummaryORM.flow_id == flow_id)
            )
            result = await s.execute(statement)
            row: RowMapping | None = result.mappings().first()
            if row is None:
                raise NotFoundError(f"Flow summary for flow {flow_id} not found")
            return FlowSummary.model_validate(dict(row))
