from __future__ import annotations

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from datetime import datetime
from sqlmodel import Field, SQLModel
from pydantic import BaseModel, field_serializer, field_validator
from typing import Literal, Optional

from mitmproxy import http
from vex_cli.flow_helper import (
    extract_url_path,
    extract_query,
    extract_extension,
    extract_http_title,
    extract_mime,
    request_total_size,
    response_total_size,
    uses_tls,
    has_cookies,
    flow_to_raw_request,
    flow_to_raw_response,
    calculate_response_time_ms
)

"""
All the models are SQLModel so a Pydantic and ORM model in one
or at least that's how they are advertised. But because table=True
we don't get automatic validation when objects are created or when
they are deserialized from endpoints. So we have to use this @field_serializer 
(to suppress Pydantic warnings) and also do manual validation 
with `model = Model.model_validate(model.model_dump())`.
https://github.com/fastapi/sqlmodel/issues/52
https://github.com/fastapi/sqlmodel/discussions/925
"""
# internal
@dataclass
class VexServerInfo: 
    server_address: str
    proxy_port: int
    api_port: int

class Project(SQLModel, table=True):
    __tablename__ = "projects"  # type: ignore
    id: uuid.UUID = Field(
        nullable=False,
        primary_key=True,
        default_factory=uuid.uuid4
    )
    name: str = Field(nullable=False, unique=True)
    created_at: datetime = Field(
        nullable=False,
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        nullable=False,
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    
    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v
        
    @field_serializer("id")
    def serialize_id(self, id: uuid.UUID):
        return str(id)
    
class RequestSummary(SQLModel, table=True):
    """A flow request summary created when the flow is captured"""
    __tablename__ = "requests"  # type: ignore

    id: int = Field(default=None, primary_key=True)
    flow_id: uuid.UUID = Field(nullable=False, index=True, unique=True)
    host: str = Field(nullable=False, index=True)
    method: str = Field(nullable=False, index=True)
    path: str = Field(nullable=False, index=True)
    request_size: int = Field(nullable=False, index=True)
    is_tls: bool = Field(nullable=False, index=True)
    query: str | None = Field(nullable=True, index=True)
    file_extension: str | None = Field(nullable=True, index=True)
    timestamp: float = Field(nullable=False, index=True)
    
    @field_serializer("flow_id")
    def serialize_id(self, flow_id: uuid.UUID):
        return str(flow_id)
    
    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> RequestSummary:
        return cls(
            flow_id=uuid.UUID(flow.id),
            host=flow.request.host,
            method=flow.request.method,
            path=extract_url_path(flow),
            request_size=request_total_size(flow),
            is_tls=uses_tls(flow),
            query=extract_query(flow),
            file_extension=extract_extension(flow),
            timestamp=datetime.timestamp(datetime.now())
        )

class ResponseSummary(SQLModel,table=True):
    """A flow response summary created when the flow is captured."""
    __tablename__ = "responses"  # type: ignore

    id: int = Field(default=None, primary_key=True)
    flow_id: uuid.UUID = Field(nullable=False, index=True, unique=True)
    status_code: int = Field(nullable=False, index=True)
    response_size: int = Field(nullable=False, index=True)
    mime: str | None = Field(nullable=True, index=True)
    http_title: str | None = Field(nullable=True, index=True)
    has_cookie_set: bool = Field(nullable=False, index=True)
    duration_ms: int = Field(nullable=False, index=True)
    timestamp: float = Field(nullable=False, index=True)
    
    @field_serializer("flow_id")
    def serialize_id(self, flow_id: uuid.UUID):
        return str(flow_id)

    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> ResponseSummary:
        return cls(
            flow_id=uuid.UUID(flow.id),
            status_code=flow.response.status_code, # type: ignore
            response_size=response_total_size(flow),
            mime=extract_mime(flow),
            http_title=extract_http_title(flow),
            has_cookie_set=has_cookies(flow),
            duration_ms=calculate_response_time_ms(flow),
            timestamp=datetime.timestamp(datetime.now())
        )
        
        
class RawRequest(SQLModel, table=True):
    """Raw HTTP request"""
    __tablename__ = "raw_requests"  # type: ignore

    id: uuid.UUID = Field(nullable=False, primary_key=True) # flow_id
    data: bytes = Field(nullable=False, index=True)
    
    @field_serializer("id")
    def serialize_id(self, id: uuid.UUID):
        return str(id)

    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> RawRequest:
        return cls(
            id=uuid.UUID(flow.id),
            data=flow_to_raw_request(flow)
        )
        
class RawResponse(SQLModel,table=True):
    """Raw HTTP response"""
    __tablename__ = "raw_responses"  # type: ignore

    id: uuid.UUID = Field(nullable=False, primary_key=True) # flow_id
    data: bytes = Field(nullable=True, index=True)

    @field_serializer("id")
    def serialize_id(self, id: uuid.UUID):
        return str(id)

    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> RawResponse:
        return cls(
            id=uuid.UUID(flow.id),
            data=flow_to_raw_response(flow) # type: ignore
        )

class ResponseStatus(BaseModel):
    """
    We return this if FastAPI endpoints to return the status of the operation
    and any other logging info for the client
    """
    status: Literal["Success", "Failure"]
    msg: Optional[str]
    
class PIDData(BaseModel):
    """Data that will be saved to the vex.pid file"""
    pid: int
    host: str
    proxy_port: int
    api_port: int
