from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, Index, Integer, LargeBinary, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectORM(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class RequestSummaryORM(Base):
    """A flow request summary created when the flow is captured."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, nullable=False)
    host: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    request_size: Mapped[int] = mapped_column(Integer, nullable=False)
    is_tls: Mapped[bool] = mapped_column(Boolean, nullable=False)
    query: Mapped[str | None] = mapped_column(String, nullable=True)
    file_extension: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index("ix_requests_flow_id", "flow_id"),
        Index("ix_requests_host", "host"),
        Index("ix_requests_timestamp", "timestamp"),
    )


class ResponseSummaryORM(Base):
    """A flow response summary created when the flow is captured."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime: Mapped[str | None] = mapped_column(String, nullable=True)
    http_title: Mapped[str | None] = mapped_column(String, nullable=True)
    cookie: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index("ix_responses_flow_id", "flow_id"),
        Index("ix_responses_status_code", "status_code"),
        Index("ix_responses_timestamp", "timestamp"),
    )


class RawRequestORM(Base):
    """Raw HTTP request bytes keyed by flow_id."""

    __tablename__ = "raw_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # flow_id
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class RawResponseORM(Base):
    """Raw HTTP response bytes keyed by flow_id."""

    __tablename__ = "raw_responses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)  # flow_id
    data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class ScopeORM(Base):
    """Scopes that are set by the user."""

    __tablename__ = "scopes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    definitions: Mapped[str] = mapped_column(
        String, nullable=False, default='{"allow":[],"deny":[]}'
    )
