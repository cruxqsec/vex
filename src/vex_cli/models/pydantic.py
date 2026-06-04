from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union
import json
from uuid import UUID

from mitmproxy import http
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    IPvAnyAddress,
    AnyUrl,
    TypeAdapter,
)

from vex_cli.flow_helper import (
    calculate_response_time_ms,
    extract_extension,
    extract_http_title,
    extract_mime,
    extract_query,
    extract_url_path,
    extract_cookies,
    flow_to_raw_request,
    flow_to_raw_response,
    has_cookies,
    request_total_size,
    response_total_size,
    uses_tls,
)
from vex_cli.models.orm import (
    RawRequestORM,
    RawResponseORM,
    RequestSummaryORM,
    ResponseSummaryORM,
    ProjectORM,
    ScopeORM,
)

# For Pydantic->ORM conversion
_orm_config = ConfigDict(from_attributes=True)

_ip_adapter = TypeAdapter(IPvAnyAddress)
_url_adapter = TypeAdapter(AnyUrl)


# validator
def check_ip(v: str) -> str:
    _ip_adapter.validate_python(v)
    return v


def check_domain(v: str) -> str:
    if "://" in v:
        raise ValueError(f"URLs with schemes are not allowed, got: {v!r}")

    url = _url_adapter.validate_python(f"https://{v}")

    if not url.host:
        raise ValueError(f"Invalid domain: no host found in '{v}'")
    if url.path and url.path != "/":
        raise ValueError(f"Domain must not contain a path: '{url.path}'")
    if url.query:
        raise ValueError(f"Domain must not contain query parameters: '{url.query}'")
    if url.fragment:
        raise ValueError(f"Domain must not contain a fragment: '#{url.fragment}'")

    return v


IPStr = Annotated[str, BeforeValidator(check_ip)]
PortNumber = Annotated[int, Field(ge=0, le=65535)]
DomainStr = Annotated[str, BeforeValidator(check_domain)]


class VexServerInfo(BaseModel):
    """
    Object with the server information of vex_cli.
    """

    server_address: IPStr
    proxy_port: PortNumber
    api_port: PortNumber


class PIDData(BaseModel):
    """
    Data that will be saved to the vex.pid file.
    """

    pid: int = Field(ge=1)
    host: IPStr
    proxy_port: PortNumber
    api_port: PortNumber


class ResponseStatus(BaseModel):
    """
    We return this from endpoints where we don't return any other data.
    """

    status: Literal["Success", "Failure"]
    msg: str


class CountResponse(BaseModel):
    count: int


class Project(BaseModel):
    """Vex project object."""

    model_config = _orm_config

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    def to_orm(self) -> ProjectORM:
        return ProjectORM(**self.model_dump())


class ProjectCreate(BaseModel):
    """Used when creating or updating a project — id and timestamps are DB-generated."""

    name: str


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
            flow_id=UUID(flow.id),
            host=flow.request.host,
            method=flow.request.method,
            path=extract_url_path(flow),
            request_size=request_total_size(flow),
            is_tls=uses_tls(flow),
            query=extract_query(flow),
            file_extension=extract_extension(flow),
            timestamp=datetime.timestamp(datetime.now()),
        )

    def to_orm(self) -> RequestSummaryORM:
        return RequestSummaryORM(**self.model_dump())


class ResponseSummary(BaseModel):
    """A flow response summary created when the flow is captured."""

    model_config = _orm_config

    id: int | None = None
    flow_id: UUID
    status_code: int
    response_size: int
    mime: str | None
    http_title: str | None
    cookie: str
    duration_ms: int
    timestamp: float

    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> ResponseSummary:
        return cls(
            flow_id=UUID(flow.id),
            status_code=flow.response.status_code,  # type: ignore
            response_size=response_total_size(flow),
            mime=extract_mime(flow),
            http_title=extract_http_title(flow),
            cookie=extract_cookies(flow),
            duration_ms=calculate_response_time_ms(flow),
            timestamp=datetime.timestamp(datetime.now()),
        )

    def to_orm(self) -> ResponseSummaryORM:
        return ResponseSummaryORM(**self.model_dump())


# for querying the full summaries from db
class FlowSummary(BaseModel):
    model_config = _orm_config

    # from RequestSummary (all fields)
    id: int
    flow_id: UUID
    host: str
    method: str
    path: str
    request_size: int
    is_tls: bool
    query: str | None
    file_extension: str | None
    timestamp: float

    # from ResponseSummary (excluding id, flow_id, timestamp)
    status_code: int | None = None
    response_size: int | None = None
    mime: str | None = None
    http_title: str | None = None
    cookie: str | None = None
    duration_ms: int | None = None


class RawRequest(BaseModel):
    """Raw HTTP request bytes."""

    model_config = _orm_config

    id: UUID  # flow_id
    data: bytes

    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> RawRequest:
        return cls(id=UUID(flow.id), data=flow_to_raw_request(flow))

    def to_orm(self) -> RawRequestORM:
        return RawRequestORM(**self.model_dump())


class RawResponse(BaseModel):
    """Raw HTTP response bytes."""

    model_config = _orm_config

    id: UUID  # flow_id
    data: bytes | None

    @classmethod
    def from_flow(cls, flow: http.HTTPFlow) -> RawResponse:
        return cls(
            id=UUID(flow.id),
            data=flow_to_raw_response(flow),  # type: ignore — caller ensures response exists
        )

    def to_orm(self) -> RawResponseORM:
        return RawResponseORM(**self.model_dump())


ScopeEndpoint = Union[IPStr, DomainStr]


class Scope(BaseModel):
    """
    Scope set on the proxy.
    Composed of allow and deny endpoints.
    """

    id: int
    allow_endpoints: list[ScopeEndpoint]
    deny_endpoints: list[ScopeEndpoint]

    def to_orm(self) -> ScopeORM:
        return ScopeORM(
            id=self.id,
            definitions=json.dumps(
                {"allow": list(self.allow_endpoints), "deny": list(self.deny_endpoints)}
            ),
        )

    @classmethod
    def from_orm(cls, orm: ScopeORM) -> "Scope":
        raw = json.loads(orm.definitions) if orm.definitions else {}
        return cls(
            id=orm.id,
            allow_endpoints=raw.get("allow", []),
            deny_endpoints=raw.get("deny", []),
        )
