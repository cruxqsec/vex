import pytest
from unittest.mock import MagicMock

from vex_cli.flow_scope import FlowScope
from vex_cli.models.pydantic import Scope


@pytest.fixture
def flow_scope():
    return FlowScope()


@pytest.fixture
def mock_scope_allow_only():
    scope = MagicMock(spec=Scope)
    scope.allow_endpoints = ["example.com", "127.0.0.1"]
    scope.deny_endpoints = []
    return scope


@pytest.fixture
def mock_scope_deny_only():
    scope = MagicMock(spec=Scope)
    scope.allow_endpoints = []
    scope.deny_endpoints = ["malicious.com", "192.168.1.1"]
    return scope


@pytest.fixture
def mock_scope_both():
    scope = MagicMock(spec=Scope)
    scope.allow_endpoints = ["example.com", "127.0.0.1"]
    scope.deny_endpoints = ["evil.com"]
    return scope


@pytest.fixture
def mock_scope_empty():
    scope = MagicMock(spec=Scope)
    scope.allow_endpoints = []
    scope.deny_endpoints = []
    return scope


def test_init_sets_active_scope_to_none(flow_scope):
    assert flow_scope.get_active_scope() is None


def test_set_active_scope_sets_scope(flow_scope, mock_scope_allow_only):
    flow_scope.set_active_scope(mock_scope_allow_only)

    assert flow_scope.get_active_scope() is mock_scope_allow_only


def test_set_active_scope_can_be_set_to_none(flow_scope, mock_scope_allow_only):
    flow_scope.set_active_scope(mock_scope_allow_only)
    flow_scope.set_active_scope(None)

    assert flow_scope.get_active_scope() is None


def test_get_active_scope_returns_set_scope(flow_scope, mock_scope_deny_only):
    flow_scope.set_active_scope(mock_scope_deny_only)

    assert flow_scope.get_active_scope() is mock_scope_deny_only


def test_apply_scope_returns_true_when_no_active_scope(flow_scope):
    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("random.com") is True


def test_apply_scope_returns_true_when_endpoints_empty(flow_scope, mock_scope_empty):
    flow_scope.set_active_scope(mock_scope_empty)

    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("192.168.1.1") is True


def test_apply_scope_deny_endpoints_blocks_host(flow_scope, mock_scope_deny_only):
    flow_scope.set_active_scope(mock_scope_deny_only)

    assert flow_scope.apply_scope("malicious.com") is False
    assert flow_scope.apply_scope("192.168.1.1") is False


def test_apply_scope_deny_endpoints_allows_other_hosts(
    flow_scope, mock_scope_deny_only
):
    flow_scope.set_active_scope(mock_scope_deny_only)

    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("127.0.0.1") is True


def test_apply_scope_allow_endpoints_allows_host(flow_scope, mock_scope_allow_only):
    flow_scope.set_active_scope(mock_scope_allow_only)

    assert flow_scope.apply_scope("example.com") is True
    assert flow_scope.apply_scope("127.0.0.1") is True


def test_apply_scope_allow_endpoints_blocks_other_hosts(
    flow_scope, mock_scope_allow_only
):
    flow_scope.set_active_scope(mock_scope_allow_only)

    assert flow_scope.apply_scope("malicious.com") is False
    assert flow_scope.apply_scope("192.168.1.1") is False


def test_apply_scope_deny_takes_precedence_over_allow(flow_scope, mock_scope_both):
    flow_scope.set_active_scope(mock_scope_both)

    # evil.com is in deny_endpoints, should be blocked
    assert flow_scope.apply_scope("evil.com") is False

    # example.com is in allow_endpoints, should be allowed
    assert flow_scope.apply_scope("example.com") is True

    # random.com not in either, should be allowed (allow_endpoints exists)
    assert flow_scope.apply_scope("random.com") is False


def test_apply_scope_with_allow_and_deny_allows_unless_denied(
    flow_scope, mock_scope_both
):
    flow_scope.set_active_scope(mock_scope_both)

    # 127.0.0.1 is in allow, not in deny, should be allowed
    assert flow_scope.apply_scope("127.0.0.1") is True
