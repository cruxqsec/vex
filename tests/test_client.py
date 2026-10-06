import asyncio

import httpx
import pytest
from httpx import AsyncClient, MockTransport

import vex_client.api.client as client_module
from vex_client.api.client import ApiClient


@pytest.fixture(autouse=True)
def _no_global_state():
    # ApiClient is app-owned; nothing global to reset across tests
    yield


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/health":
        return httpx.Response(200, json={"pid": 42})
    if request.url.path == "/api/summary/count":
        return httpx.Response(200, json={"count": 7})
    return httpx.Response(404, text="nope")


def _make(host: str = "127.0.0.1", port: int = 9000) -> ApiClient:
    transport = MockTransport(_handler)
    injected = AsyncClient(base_url=f"http://{host}:{port}", transport=transport)
    return ApiClient(host, port, client=injected)


@pytest.mark.asyncio
async def test_base_url_host_port():
    api = _make()
    assert api.base_url == "http://127.0.0.1:9000"


@pytest.mark.asyncio
async def test_default_timeout_explicit():
    api = _make()
    assert api.client.timeout.connect == 5.0
    assert api.client.timeout.read == 5.0
    await api.aclose()


@pytest.mark.asyncio
async def test_sections_share_one_httpx_client():
    api = _make()
    assert api.summaries._client is api.scope._client
    assert api.scope._client is api.projects._client
    assert api.projects._client is api.raw._client
    assert api.raw._client is api.health._client
    assert api.summaries._client is api.client
    await api.aclose()


@pytest.mark.asyncio
async def test_sections_hit_relative_paths_via_mock_transport():
    api = _make()
    assert await api.summaries.count_flows() == 7
    assert await api.health.check_health_pid() == 42
    await api.aclose()


@pytest.mark.asyncio
async def test_aclose_idempotent():
    api = _make()
    await api.aclose()
    assert api.is_closed
    await api.aclose()  # second close is a no-op, no error


@pytest.mark.asyncio
async def test_async_context_manager_closes_on_exit():
    async with _make() as api:
        assert not api.is_closed
    assert api.is_closed


def test_no_module_level_singleton_left():
    assert not hasattr(client_module, "get_client")
    assert not hasattr(client_module, "aclose_client")
    assert not hasattr(client_module, "_client")