import httpx

from vex_client.api.client import ApiClient


async def test_client_creates_shared_http_client_and_section_apis() -> None:
    api = ApiClient("127.0.0.1", 8123)
    try:
        assert api.base_url == "http://127.0.0.1:8123"
        assert api._client.base_url == httpx.URL(api.base_url)
        assert api._client.timeout.connect == 5.0
        assert all(
            section_api._client is api._client
            for section_api in (
                api.health,
                api.projects,
                api.raw,
                api.scope,
                api.summaries,
            )
        )
        assert api._client.is_closed is False
    finally:
        await api.close()

    assert api._client.is_closed is True


async def test_client_close_closes_injected_client() -> None:
    client = httpx.AsyncClient(
        base_url="http://vex.test",
        transport=httpx.MockTransport(lambda request: httpx.Response(200)),
    )

    api = ApiClient("vex.test", 8123, client=client)
    assert api._client is client
    assert client.is_closed is False

    await api.close()
    await api.close()
    assert client.is_closed is True
