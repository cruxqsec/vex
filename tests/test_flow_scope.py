from vex_cli.flow_scope import FlowScope
from vex_cli.models.pydantic import Scope


def test_init_sets_active_scope_to_none(flow_scope: FlowScope) -> None:
    assert flow_scope.get_active_scope() is None


def test_set_active_scope_sets_scope(flow_scope: FlowScope, allow_only_scope: Scope) -> None:
    flow_scope.set_active_scope(allow_only_scope)

    assert flow_scope.get_active_scope() is allow_only_scope


def test_set_active_scope_can_be_set_to_none(flow_scope: FlowScope, allow_only_scope: Scope) -> None:
    flow_scope.set_active_scope(allow_only_scope)
    flow_scope.set_active_scope(None)

    assert flow_scope.get_active_scope() is None


def test_apply_scope_returns_true_when_no_active_scope(flow_scope: FlowScope) -> None:
    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("random.com") is True


def test_apply_scope_returns_true_when_endpoints_empty(flow_scope: FlowScope, empty_scope: Scope) -> None:
    flow_scope.set_active_scope(empty_scope)

    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("192.168.1.1") is True


def test_apply_scope_deny_endpoints_blocks_host(flow_scope: FlowScope, deny_only_scope: Scope) -> None:
    flow_scope.set_active_scope(deny_only_scope)

    assert flow_scope.apply_scope("malicious.com") is False
    assert flow_scope.apply_scope("192.168.1.1") is False


def test_apply_scope_deny_endpoints_allows_other_hosts(flow_scope: FlowScope, deny_only_scope: Scope) -> None:
    flow_scope.set_active_scope(deny_only_scope)

    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("127.0.0.1") is True


def test_apply_scope_allow_endpoints_allows_host(flow_scope: FlowScope, allow_only_scope: Scope) -> None:
    flow_scope.set_active_scope(allow_only_scope)

    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("127.0.0.1") is True


def test_apply_scope_allow_endpoints_blocks_other_hosts(flow_scope: FlowScope, allow_only_scope: Scope) -> None:
    flow_scope.set_active_scope(allow_only_scope)

    assert flow_scope.apply_scope("malicious.com") is False
    assert flow_scope.apply_scope("192.168.1.1") is False


def test_apply_scope_deny_takes_precedence_over_allow(flow_scope: FlowScope, scope: Scope) -> None:
    flow_scope.set_active_scope(scope)

    # evil.com is in deny_endpoints
    assert flow_scope.apply_scope("evil.com") is False

    # example.com is in allow_endpoints
    assert flow_scope.apply_scope("192.168.1.1") is True

    # random.com not in either, should be blocked
    assert flow_scope.apply_scope("random.com") is False
