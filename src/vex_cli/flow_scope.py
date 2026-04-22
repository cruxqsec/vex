from vex_cli.models.pydantic import Scope


class FlowScope:
    """Mantains the active scope ruleset and applys it to the proxy."""

    def __init__(self) -> None:
        self._active_scope: Scope | None = None

    def get_active_scope(self) -> Scope | None:
        return self._active_scope

    def set_active_scope(self, scope: Scope | None) -> None:
        self._active_scope = scope

    def apply_scope(self, host: str) -> bool:
        """Prevents the flow of request/responses based on allow/deny endpoint set."""
        if self._active_scope is None:
            return True
        
        if not self._active_scope.allow_endpoints and not self._active_scope.deny_endpoints:
            return True

        if host in self._active_scope.deny_endpoints:
            return False
        
        if self._active_scope.allow_endpoints:
            return host in self._active_scope.allow_endpoints

        return True
