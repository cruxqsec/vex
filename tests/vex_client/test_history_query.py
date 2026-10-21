from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from vex_cli.models.pydantic import FlowSummary, Scope
from vex_client.history.query import (
    SEARCH_FIELDS,
    SearchTerm,
    filter_summaries,
    matches_scope,
    matches_search,
    parse_search_query,
)


@pytest.fixture
def summary():
    return FlowSummary(
        id=1, flow_id=uuid4(), host="example.com", method="GET",
        path="/Docs/index.HTML", request_size=10, is_tls=True,
        query="next=https://example.com:443", file_extension="HTML",
        timestamp=1.0, status_code=200, mime="text/html",
        http_title="Welcome Home", cookie="Session=ABC",
    )


def test_search_fields():
    assert SEARCH_FIELDS == {
        "host": "host", "method": "method", "path": "path", "query": "query",
        "status": "status_code", "mime": "mime", "title": "http_title",
        "ext": "file_extension", "cookie": "cookie",
    }


def test_parse_normalizes_and_returns_immutable_terms():
    terms = parse_search_query("  HoSt:EXAMPLE\tGET\nTITLE:Welcome ")
    assert terms == (
        SearchTerm("host", "example"), SearchTerm(None, "get"),
        SearchTerm("title", "welcome"),
    )
    with pytest.raises(FrozenInstanceError):
        terms[0].value = "changed"  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("token, reason", [
    ("unknown:value", "unknown prefix"),
    ("https://example.com", "unknown prefix"),
    ("http://example.com:8080/path", "unknown prefix"),
    (":value", "unknown prefix"),
    ("host:", "empty value"),
    ("STATUS:", "empty value"),
])
@pytest.mark.parametrize("template", ["{}", "host:example {}", "{} method:get"])
def test_validates_entire_query(token, reason, template):
    with pytest.raises(ValueError) as error:
        parse_search_query(template.format(token))
    assert token in str(error.value)
    assert reason in str(error.value)


@pytest.mark.parametrize("prefix", SEARCH_FIELDS)
def test_every_prefix_requires_a_value(prefix):
    with pytest.raises(ValueError, match="empty value"):
        parse_search_query(f"{prefix}:")


def test_colons_inside_values_are_valid(summary):
    terms = parse_search_query("QUERY:https://EXAMPLE.com:443 cookie::")
    assert terms == (
        SearchTerm("query", "https://example.com:443"), SearchTerm("cookie", ":"),
    )
    assert matches_search(summary, terms[:1])


@pytest.mark.parametrize("text", [
    "host:AMPLE", "method:ge", "path:DOCS", "query:NEXT=", "status:20",
    "mime:HTML", "title:WELCOME", "ext:html", "cookie:session=abc",
    "AMPLE", "ge", "DOCS", "NEXT=", "20", "HTML", "WELCOME", "session=abc",
    "HOST:EXAMPLE method:get docs TITLE:home status:00",
])
def test_case_insensitive_substrings_and_plain_terms(summary, text):
    assert matches_search(summary, parse_search_query(text))


@pytest.mark.parametrize("text", [
    "host:example method:post", "welcome missing", "path:example",
    "status:not-a-number", "status:>199",
])
def test_all_terms_required_and_status_is_only_text(summary, text):
    assert not matches_search(summary, parse_search_query(text))


@pytest.mark.parametrize("text", ["", " \t\n "])
def test_empty_query_matches_all(summary, text):
    terms = parse_search_query(text)
    assert terms == ()
    assert matches_search(summary, terms)
    assert filter_summaries([summary], None, terms) == [summary]


def test_missing_fields_do_not_match_none(summary):
    pending = summary.model_copy(update={
        "query": None, "file_extension": None, "status_code": None,
        "mime": None, "http_title": None, "cookie": None,
    })
    assert not matches_search(pending, parse_search_query("none"))
    assert not matches_search(pending, parse_search_query("status:20"))
    assert matches_search(pending, ())


@pytest.mark.parametrize("allow, deny, expected", [
    ([], [], True),
    (["example.com"], [], True),
    (["other.com"], [], False),
    ([], ["example.com"], False),
    (["example.com"], ["example.com"], False),
    (["example.com"], ["other.com"], True),
    (["sub.example.com"], [], False),
    ([], ["sub.example.com"], True),
])
def test_scope_exact_hosts_and_deny_precedence(summary, allow, deny, expected):
    scope = Scope(id=1, name="test", allow_endpoints=allow, deny_endpoints=deny)
    assert matches_scope(summary, scope) is expected


def test_no_scope(summary):
    assert matches_scope(summary, None)


def test_filter_preserves_order_and_objects_and_combines_filters(summary):
    other = summary.model_copy(update={"host": "other.com"})
    post = summary.model_copy(update={"method": "POST"})
    earlier = summary.model_copy(update={"id": 2, "timestamp": 0.0})
    items = [summary, other, post, earlier]
    scope = Scope(id=1, name="test", allow_endpoints=["example.com"], deny_endpoints=[])
    result = filter_summaries(iter(items), scope, parse_search_query("method:get"))
    assert result == [summary, earlier]
    assert result[0] is summary
    assert result[1] is earlier
    assert items == [summary, other, post, earlier]
    assert filter_summaries([], scope, ()) == []


def test_scope_is_applied_before_search(summary, monkeypatch):
    scope = Scope(id=1, name="test", allow_endpoints=[], deny_endpoints=[summary.host])

    def unexpected_search(*args):
        pytest.fail("Search must not run for an out-of-scope summary")

    monkeypatch.setattr("vex_client.history.query.matches_search", unexpected_search)
    assert filter_summaries([summary], scope, parse_search_query("host:example")) == []
