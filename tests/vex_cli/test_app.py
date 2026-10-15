import logging

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from vex_cli.app import status_for
from vex_cli.errors import (
    AppException,
    ConflictError,
    DatabaseError,
    NoProjectActiveError,
    NotFoundError,
)

PATH = "/_test/raise"


class SpecialNotFound(NotFoundError):
    pass


class Out(BaseModel):
    n: int


@pytest.fixture
def raise_on_request(app):
    def _register(exc):
        async def endpoint():
            raise exc

        app.add_api_route(PATH, endpoint)

    return _register


@pytest_asyncio.fixture
async def lenient_client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def app_logs(caplog):
    return [r for r in caplog.records if r.name == "vex_cli.app"]


@pytest.mark.parametrize(
    ("exc", "status"),
    [
        (NotFoundError("x"), 404),
        (ConflictError("x"), 409),
        (NoProjectActiveError(), 409),
        (DatabaseError("x"), 500),
        (AppException("x"), 500),
        (SpecialNotFound("x"), 404),
    ],
)
def test_status_for(exc, status):
    assert status_for(exc) == status


async def test_app_exception_becomes_json_error(client, raise_on_request):
    raise_on_request(NotFoundError("nope"))

    resp = await client.get(PATH)

    assert resp.status_code == 404
    assert resp.json() == {"error": "NotFoundError", "message": "nope"}


async def test_client_errors_are_not_logged_as_errors(
    client, raise_on_request, caplog
):
    raise_on_request(ConflictError("dup"))

    with caplog.at_level(logging.DEBUG):
        await client.get(PATH)

    assert app_logs(caplog) == []


async def test_server_errors_are_logged_with_request_and_traceback(
    client, raise_on_request, caplog
):
    raise_on_request(DatabaseError("db down"))

    with caplog.at_level(logging.DEBUG):
        resp = await client.get(PATH)

    (record,) = app_logs(caplog)
    assert resp.status_code == 500
    assert record.levelno == logging.ERROR
    assert f"GET {PATH}" in record.getMessage()
    assert record.exc_info is not None


async def test_unexpected_exception_returns_generic_500(
    lenient_client, raise_on_request, caplog
):
    raise_on_request(RuntimeError("secret detail"))

    with caplog.at_level(logging.DEBUG):
        resp = await lenient_client.get(PATH)

    assert resp.status_code == 500
    assert resp.json() == {
        "error": "InternalServerError",
        "message": "Something went wrong",
    }
    assert "secret detail" not in resp.text
    assert any(r.exc_info for r in app_logs(caplog))


async def test_response_serialization_bug_returns_500(app, lenient_client):
    async def endpoint():
        return {"n": "not-an-int"}

    app.add_api_route("/_test/bad", endpoint, response_model=Out)

    resp = await lenient_client.get("/_test/bad")

    assert resp.status_code == 500
    assert resp.json()["error"] == "InternalServerError"
