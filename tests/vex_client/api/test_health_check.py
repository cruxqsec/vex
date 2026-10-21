import httpx
import pytest

from vex_client.api.health_check import HealthApi
from vex_client.process import INACTIVE_PROCESS


def _response(request: httpx.Request, status_code: int, json: object = None) -> httpx.Response:
    if json is None:
        return httpx.Response(status_code, request=request)
    return httpx.Response(status_code, json=json, request=request)


@pytest.mark.parametrize("request_error", [httpx.TimeoutException, httpx.ConnectError])
async def test_health_check_handshake_returns_false_on_request_error(
    request_error: type[httpx.RequestError],
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise request_error("offline", request=request)

    async with httpx.AsyncClient(
        base_url="http://vex.test", transport=httpx.MockTransport(handler)
    ) as client:
        assert await HealthApi(client).health_check_handshake() is False

    assert len(requests) == 1
    assert requests[0].url.path == "/health"


async def test_health_check_handshake_returns_false_on_non_success_status() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _response(request, 503)

    async with httpx.AsyncClient(
        base_url="http://vex.test", transport=httpx.MockTransport(handler)
    ) as client:
        assert await HealthApi(client).health_check_handshake() is False

    assert len(requests) == 1
    assert requests[0].url.path == "/health"


async def test_health_check_handshake_returns_true_on_success() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _response(request, 200)

    async with httpx.AsyncClient(
        base_url="http://vex.test", transport=httpx.MockTransport(handler)
    ) as client:
        assert await HealthApi(client).health_check_handshake() is True

    assert len(requests) == 1
    assert requests[0].url.path == "/health"


async def test_check_health_pid_returns_pid_from_successful_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _response(request, 200, {"pid": 4321})

    async with httpx.AsyncClient(
        base_url="http://vex.test", transport=httpx.MockTransport(handler)
    ) as client:
        assert await HealthApi(client).check_health_pid() == 4321


@pytest.mark.parametrize(
    "response",
    [
        lambda request: _response(request, 503),
        lambda request: httpx.Response(200, text="not json", request=request),
        lambda request: _response(request, 200, {"status": "ok"}),
    ],
    ids=["non-success-status", "invalid-json", "missing-pid"],
)
async def test_check_health_pid_returns_inactive_for_invalid_responses(
    response,
) -> None:
    async with httpx.AsyncClient(
        base_url="http://vex.test",
        transport=httpx.MockTransport(response),
    ) as client:
        assert await HealthApi(client).check_health_pid() == INACTIVE_PROCESS


async def test_check_health_pid_returns_inactive_on_request_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(
        base_url="http://vex.test", transport=httpx.MockTransport(handler)
    ) as client:
        assert await HealthApi(client).check_health_pid() == INACTIVE_PROCESS
