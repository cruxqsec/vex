import httpx

from vex_client.api.health_check import HealthApi
from vex_client.api.project_api import ProjectsApi
from vex_client.api.raw_api import RawApi
from vex_client.api.scope_api import ScopeApi
from vex_client.api.summaries_api import SummariesApi


class ApiClient:
    """Owns the pooled httpx client for one vex-cli server (host, port).

    Exposes the section APIs (health, projects, raw, scope, summaries),
    which all share the single underlying httpx.AsyncClient.
    """

    def __init__(
        self,
        host: str,
        port: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = f"http://{host}:{port}"
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url, timeout=5.0
        )
        self.health = HealthApi(self._client)
        self.projects = ProjectsApi(self._client)
        self.raw = RawApi(self._client)
        self.scope = ScopeApi(self._client)
        self.summaries = SummariesApi(self._client)

    @property
    def client(self) -> httpx.AsyncClient:
        """The shared underlying httpx client (used by the section APIs)."""
        return self._client

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    async def aclose(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> "ApiClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
