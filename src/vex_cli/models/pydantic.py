from uuid import UUID
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, Field, IPvAnyAddress, ConfigDict

# For Pydantic->ORM conversion
_orm_config = ConfigDict(from_attributes=True)

PortNumber = Annotated[int, Field(ge=0, le=65535)]

class VexServerInfo(BaseModel):
    """
    Object with the server information of vex_cli.
    """

    server_address: IPvAnyAddress
    proxy_port: PortNumber
    api_port: PortNumber

class PIDData(BaseModel):
    """
    Data that will be saved to the vex.pid file.
    """

    pid: int = Field(ge=0)
    host: IPvAnyAddress
    proxy_port: PortNumber
    api_port: PortNumber

class ResponseStatus(BaseModel):
    """
    We return this from endpoints where we don't return any other data.
    """

    status: Literal["Success", "Failure"]
    msg: str

class Project(BaseModel):
    """Vex project object."""
    model_config = _orm_config
 
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

class RequestSummary(BaseModel):
    """A flow request summary created when the flow is captured."""
 
    model_config = _orm_config
 
    id: int | None = None
    flow_id: UUID
    host: str
    method: str
    path: str
    request_size: int
    is_tls: bool
    query: str | None
    file_extension: str | None
    timestamp: float
 
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
            timestamp=datetime.timestamp(datetime.now()),
        )
 
 
class ResponseSummary(BaseModel):
    """A flow response summary created when the flow is captured."""
 
    model_config = _orm_config
 
    id: int | None = None
    flow_id: uuid.UUID
    status_code: int
    response_size: int
    mime: str | None
    http_title: str | None
    has_cookie_set: bool
    duration_ms: int
    timestamp: float
 
    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> ResponseSummary:
        return cls(
            flow_id=uuid.UUID(flow.id),
            status_code=flow.response.status_code,  # type: ignore
            response_size=response_total_size(flow),
            mime=extract_mime(flow),
            http_title=extract_http_title(flow),
            has_cookie_set=has_cookies(flow),
            duration_ms=calculate_response_time_ms(flow),
            timestamp=datetime.timestamp(datetime.now()),
        )
 
 
class RawRequest(BaseModel):
    """Raw HTTP request bytes."""
 
    model_config = _orm_config
 
    id: uuid.UUID  # flow_id
    data: bytes
 
    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> RawRequest:
        return cls(id=uuid.UUID(flow.id), data=flow_to_raw_request(flow))
 
 
class RawResponse(BaseModel):
    """Raw HTTP response bytes."""
 
    model_config = _orm_config
 
    id: uuid.UUID  # flow_id
    data: bytes | None
 
    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> RawResponse:
        return cls(
            id=uuid.UUID(flow.id),
            data=flow_to_raw_response(flow),  # type: ignore — caller ensures response exists
        )
 
